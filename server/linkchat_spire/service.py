"""Room transport and durable snapshots. Designed for a single ASGI worker."""
from spire_server.ids import Id, new_id
import asyncio
from anyio import CancelScope
import hashlib
import json
import uuid
import weakref
import time
from urllib.parse import urlsplit
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict, ValidationError
from sqlalchemy import String, Text, Integer, DateTime, select, update, delete, UniqueConstraint, inspect, or_, and_, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from spire_server.db import SessionLocal, get_db
from spire_server.passwords import hash_password, verify_password
from spire_server.auth import (COOKIE_NAME, SpireApiError, SpirePrincipal, authenticate_session,
                               authorize_spire, extract_bearer_token as _bearer_token, spire_identity)
from .engine import new_run, player, apply, view, InvalidAction
from .text import previews, battle_log, catalog
from .server.delivery import Delivery
from .server.latency import Timing, logger
from .content import RULES_VERSION, CONTENT_VERSION, SCHEMA_VERSION, PROTOCOL_VERSION, PHASES

_ready=False
def require_ready():
    if not _ready:raise SpireApiError(503,'spire_unavailable','游戏模块暂不可用，聊天不受影响。',True)
router=APIRouter(tags=['spire-extension'],dependencies=[Depends(require_ready)])
class GameBase(DeclarativeBase): pass
class Room(GameBase):
    __tablename__='extension_spire_room'
    id:Mapped[str]=mapped_column(String(36),primary_key=True, default=new_id)
    owner_id:Mapped[str]=mapped_column(String(36))
    password_hash:Mapped[str|None]=mapped_column(String(255),nullable=True)
    mode:Mapped[str]=mapped_column(String(8),default='coop',server_default='coop')
    revision:Mapped[int]=mapped_column(Integer,default=0)
    finished:Mapped[int]=mapped_column(Integer,default=0)
    state:Mapped[str]=mapped_column(Text)
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.now)

class Delegation(GameBase):
    __tablename__='extension_spire_delegation'
    id:Mapped[str]=mapped_column(String(36),primary_key=True, default=new_id)
    room_id:Mapped[str]=mapped_column(String(36),index=True)
    owner_id:Mapped[str]=mapped_column(String(36))
    delegate_id:Mapped[str|None]=mapped_column(String(36),nullable=True)
    invitee_id:Mapped[str|None]=mapped_column(String(36),nullable=True)
    status:Mapped[str]=mapped_column(String(16),default='open')
    allow_sl:Mapped[int]=mapped_column(Integer,default=1)
    snapshot:Mapped[str]=mapped_column(Text)
    checkpoints:Mapped[str]=mapped_column(Text,default='[]')
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.now)
    revoke_restore:Mapped[int|None]=mapped_column(Integer,nullable=True)

class DelegationReceipt(GameBase):
    __tablename__='extension_spire_delegation_receipt'
    delegation_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    actor_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    request_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    digest:Mapped[str]=mapped_column(String(64))

class Receipt(GameBase):
    __tablename__='extension_spire_receipt'
    __table_args__=(UniqueConstraint('room_id','user_id','action_id'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True, default=new_id)
    room_id:Mapped[str]=mapped_column(String(36),index=True)
    user_id:Mapped[str]=mapped_column(String(36))
    action_id:Mapped[str]=mapped_column(String(36))
    digest:Mapped[str]=mapped_column(String(64))

class BatchReceipt(GameBase):
    __tablename__ = 'extension_spire_batch_receipt'
    room_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    digest: Mapped[str] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(Text)


class Checkpoint(GameBase):
    __tablename__='extension_spire_checkpoint'
    room_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    kind:Mapped[str]=mapped_column(String(16),primary_key=True)
    node:Mapped[str]=mapped_column(Text)
    battle_id:Mapped[str]=mapped_column(String(80),default='')
    token:Mapped[str]=mapped_column(String(36))
    snapshot:Mapped[str]=mapped_column(Text)

class ResetReceipt(GameBase):
    __tablename__='extension_spire_reset_receipt'
    room_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    user_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    message_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    token:Mapped[str]=mapped_column(String(36))
    event:Mapped[str]=mapped_column(Text)


class BattleLog(GameBase):
    __tablename__='extension_spire_battle_log'
    room_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    battle_id:Mapped[int]=mapped_column(Integer,primary_key=True)
    sequence:Mapped[int]=mapped_column(Integer,primary_key=True)
    entry:Mapped[str]=mapped_column(Text)

class WongoCredit(GameBase):
    __tablename__='extension_spire_wongo_credit'
    room_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    user_id:Mapped[str]=mapped_column(String(36),primary_key=True,index=True)
    points:Mapped[int]=mapped_column(Integer)

class VictoryCredit(GameBase):
    __tablename__='extension_spire_victory_credit'
    room_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    user_id:Mapped[str]=mapped_column(String(36),primary_key=True,index=True)
    character:Mapped[str]=mapped_column(String(24))


def load_progress(db,state):
    if state.get('continuation'):return
    state['accountProgress']={uid:{'wongoPoints':db.scalar(select(func.coalesce(func.sum(WongoCredit.points),0)).where(WongoCredit.user_id==uid))} for uid in state['players']}
    for uid,progress in state['accountProgress'].items():
        wins=dict(db.execute(select(VictoryCredit.character,func.count()).where(VictoryCredit.user_id==uid).group_by(VictoryCredit.character)).all())
        if wins:progress['characterWins']=wins

@dataclass
class Lease:
    ws:WebSocket
    uid:str
    token:str
    auth_kind:str='session'
    seat_uid:str|None=None
    read_only:bool=False
    delegation_id:str|None=None
    id:str=field(default_factory=lambda:new_id())
    send_lock:asyncio.Lock=field(default_factory=asyncio.Lock)
    actions:list[float]=field(default_factory=list)
    room_chat:bool=False
    chat_times:list[float]=field(default_factory=list)
    chat_receipts:dict=field(default_factory=dict)
    delivery:Delivery|None=None
    last_action_id:str|None=None
    follow_allowed:bool=False

leases:dict[str,dict[str,Lease]]={}
observers:dict[str,dict[str,Lease]]={}
locks=weakref.WeakValueDictionary()
def member_activity(db, channel_id, member_ids):
    """Public summary of what these channel members are playing in any room.

    Rooms are not tied to channels; `channel_id` stays for the caller's signature.
    Never expose room IDs or private game data.
    """
    if not _ready or not leases:
        return []
    from .content.characters import CHARACTERS
    from starlette.websockets import WebSocketState
    result = {}
    rooms = db.scalars(select(Room).where(Room.id.in_(list(leases)))
        .order_by(Room.updated_at.desc(), Room.id)).all()
    for room in rooms:
        state = json.loads(room.state)
        for seat, lease in list(leases.get(room.id, {}).items()):
            uid=lease.uid
            if uid not in member_ids or uid in result:
                continue
            if lease.ws.client_state != WebSocketState.CONNECTED:
                continue
            try:
                principal = authenticate_session(lease.token)
                if principal.user.id != uid:
                    continue
            except HTTPException:
                continue
            player_state = state.get('players', {}).get(str(seat))
            if not player_state:
                continue
            character = CHARACTERS.get(player_state.get('character'), {})
            result[uid] = {'userId': uid, 'characterName': character.get('name'),
                'phase': state['phase'], 'act': state.get('actIndex', 0) + 1,
                'floor': state.get('actFloor', state.get('floor', 0)),
                'paused': bool(state.get('paused', False))}
    return list(result.values())

def lock_for(room_id):
    lock=locks.get(room_id)
    if lock is None:lock=asyncio.Lock();locks[room_id]=lock
    return lock

def migrate(engine):
    global _ready
    _ready=False
    # Rooms used to belong to a channel. Saves of that layout are dropped, not
    # converted (the project had no production players yet); account progress
    # (Wongo and victory credits) is kept.
    inspector=inspect(engine)
    if inspector.has_table(Room.__tablename__) and 'channel_id' in {column['name'] for column in inspector.get_columns(Room.__tablename__)}:
        GameBase.metadata.drop_all(engine,tables=[model.__table__ for model in (Room,Receipt,BatchReceipt,Checkpoint,ResetReceipt,BattleLog)])
    GameBase.metadata.create_all(engine)
    if 'mode' not in {column['name'] for column in inspect(engine).get_columns(Room.__tablename__)}:
        with engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE extension_spire_room ADD COLUMN mode VARCHAR(8) NOT NULL DEFAULT 'coop'")
    if 'password_hash' not in {column['name'] for column in inspect(engine).get_columns(Room.__tablename__)}:
        with engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE extension_spire_room ADD COLUMN password_hash VARCHAR(255)")
    # A process restart has no live controllers. Never resume automatically.
    with Session(engine) as db:
        for room in db.scalars(select(Room).where(Room.finished==0)):
            state=json.loads(room.state)
            if state.get('rules')!=RULES_VERSION or state.get('content')!=CONTENT_VERSION:continue
            state=apply(state,next(iter(state['players'])),{'type':'pause'})
            room.state=json.dumps(state,ensure_ascii=False);room.revision=state['revision']
        db.commit()
    _ready=True

def current_delegation(db,room_id):
    grant=db.scalar(select(Delegation).join(Room,Room.id==Delegation.room_id).where(Delegation.room_id==room_id,
        Delegation.owner_id==Room.owner_id,Delegation.status.in_(('open','active'))).order_by(Delegation.created_at.desc()))
    if grant:
        snapshot=json.loads(grant.snapshot)
        if snapshot.get('rules')!=RULES_VERSION or snapshot.get('content')!=CONTENT_VERSION or snapshot.get('schema')!=SCHEMA_VERSION:return None
    return grant

def delegation_view(grant,uid):
    return {'id':grant.id,'status':grant.status,'ownerId':grant.owner_id,'delegateId':grant.delegate_id,'inviteeId':grant.invitee_id,
        'allowSl':bool(grant.allow_sl),'canRevoke':uid==grant.owner_id,
        'canRestoreBefore':grant.status=='active' and (uid==grant.owner_id or uid==grant.delegate_id and bool(grant.allow_sl))}

def control_identity(db,room,uid,control=False):
    grant=current_delegation(db,room.id)
    if grant and uid==grant.owner_id:
        if control:raise SpireApiError(409,'control_delegated','存档已托管，请先收回控制权。')
        return uid,True,grant
    if grant and grant.status=='active' and uid==grant.delegate_id:
        return grant.owner_id,False,grant
    return uid,False,None

def lease_for(room_id,seat,actor):
    lease=leases.get(room_id,{}).get(seat)
    return lease if lease and lease.uid==actor else None

async def close_control(room_id,seat=None,include_observers=False):
    active=leases.get(room_id,{})
    closing=[]
    for key in list(active):
        if seat is None or key==seat:closing.append(active.pop(key))
    if not active:leases.pop(room_id,None)
    if include_observers:closing.extend(observers.pop(room_id,{}).values())
    for lease in closing:
        if lease.delivery:await lease.delivery.close_socket(4001)
        else:
            try:await lease.ws.close(code=4001)
            except (RuntimeError,OSError):pass

def restore_delegation_snapshot(db,room,grant):
    current=json.loads(room.state);restored=json.loads(grant.snapshot)
    if restored.get('rules')!=RULES_VERSION or restored.get('content')!=CONTENT_VERSION or restored.get('schema')!=SCHEMA_VERSION:
        raise SpireApiError(409,'incompatible_room','托管前快照的规则版本不兼容。')
    if room.mode=='solo' and db.scalar(select(Room.id).where(Room.owner_id==room.owner_id,Room.mode=='solo',Room.finished==0,Room.id!=room.id)):
        raise SpireApiError(409,'save_changed','已开始另一个单人存档，不能恢复旧局。')
    from .core.continuation import rebase_phase
    rebase_phase(restored,current['phaseId']+1-restored['phaseId'])
    restored['revision']=current['revision']+1
    restored['paused']=True
    # Credits belong to this run. Never roll back progress earned in another room.
    db.execute(delete(WongoCredit).where(WongoCredit.room_id==room.id))
    db.execute(delete(VictoryCredit).where(VictoryCredit.room_id==room.id))
    db.execute(delete(Checkpoint).where(Checkpoint.room_id==room.id))
    load_progress(db,restored)
    save(db,room,restored)
    # Restoring inside the same node does not recreate its entry checkpoint.
    # Keep the original entry snapshots separately from the mid-scene handoff.
    db.flush()
    db.execute(delete(Checkpoint).where(Checkpoint.room_id==room.id))
    for checkpoint in json.loads(grant.checkpoints):
        db.add(Checkpoint(room_id=room.id,kind=checkpoint['kind'],node=checkpoint['node'],
            battle_id=checkpoint['battleId'],token=new_id(),snapshot=checkpoint['snapshot']))
    return restored

def member_room(db,room_id,uid,participant=True):
    room=db.get(Room,room_id)
    if room is None:raise SpireApiError(404,'room_not_found','房间不存在。')
    seat,_,_=control_identity(db,room,uid)
    if room.mode=='solo' and room.owner_id!=seat:raise SpireApiError(404,'room_not_found','房间不存在。')
    s=json.loads(room.state)
    if s.get('rules')!=RULES_VERSION or s.get('content')!=CONTENT_VERSION:raise SpireApiError(409,'incompatible_room','存档规则版本不同，请使用对应的后端游戏版本。')
    if participant and str(seat) not in s['players']:raise SpireApiError(403,'not_participant','请先加入房间。')
    return room,s

def principal_room(db,room_id,principal,participant=True,control=False):
    room,s=member_room(db,room_id,principal.user.id,participant)
    control_identity(db,room,principal.user.id,control)
    authorize_spire(principal,control)
    return room,s

def node_identity(s):
    node=s.get('node') or {}
    return json.dumps([s.get('actIndex',0),s.get('floor',0),node.get('id'),node.get('kind')],separators=(',',':'))


def checkpoint_sync(db,room,s):
    previous=json.loads(room.state)
    node=node_identity(s);kind=s['phase']
    old_node=node_identity(previous)
    if node!=old_node or kind in ('victory','defeat','abandoned','map'):
        db.execute(delete(Checkpoint).where(Checkpoint.room_id==room.id))
    elif kind!=previous['phase'] or s.get('paused'):
        for checkpoint in db.scalars(select(Checkpoint).where(Checkpoint.room_id==room.id)):
            checkpoint.token=new_id()
    if kind not in ('combat','event','rest','shop','treasure'):return
    battle=str(s.get('battleId','')) if kind=='combat' else ''
    entry=db.get(Checkpoint,(room.id,kind))
    entered=node!=old_node or kind!=previous['phase'] or (kind=='combat' and battle!=str(previous.get('battleId','')))
    if entered and (entry is None or entry.node!=node or entry.battle_id!=battle):
        if entry is not None:db.delete(entry);db.flush()
        db.add(Checkpoint(room_id=room.id,kind=kind,node=node,battle_id=battle,token=new_id(),snapshot=json.dumps(s,ensure_ascii=False)))


def scene_checkpoint(db,room,s):
    if s['phase'] in ('lobby','map','actComplete','ending','victory','defeat','abandoned'):return None
    # An event's battle and nested rewards belong to the original event node.
    kind='event' if (s.get('node') or {}).get('kind') in ('event','ancient') else s['phase']
    return db.get(Checkpoint,(room.id,kind)) if kind in ('combat','event','rest','shop','treasure') else None


def sl_status(db,room,s):
    entry=scene_checkpoint(db,room,s)
    available=entry is not None and entry.node==node_identity(s) and (entry.kind!='combat' or entry.battle_id==str(s.get('battleId',''))) and not s.get('paused') and not room.finished
    return {'available':available,'token':entry.token if available else None,
            'hostOnly':room.mode=='coop'}


def save(db,room,s):
    checkpoint_sync(db,room,s)
    battle_log.legacy(s)
    old=room.revision
    count=db.execute(update(Room).where(Room.id==room.id,Room.revision==old).values(state=json.dumps(s,ensure_ascii=False),revision=s['revision'],finished=int(s['phase'] in ('victory','defeat','abandoned')),updated_at=datetime.now()),execution_options={'synchronize_session':False}).rowcount
    if count!=1:raise SpireApiError(409,'stale_phase','房间已变化，请刷新。')
    # State, replayed journal and receipt commit or roll back together.
    # Replace an old encounter only when its identity changes. Normal actions
    # append, while a replay may replace its own suffix without duplicating it.
    if s.get('battleId'):
        battle_id=s['battleId']
        db.execute(delete(BattleLog).where(BattleLog.room_id==room.id,BattleLog.battle_id!=battle_id))
        existing={row.sequence:row for row in db.scalars(select(BattleLog).where(BattleLog.room_id==room.id,BattleLog.battle_id==battle_id))}
        for row in s.get('log',[]):
            encoded=json.dumps(row,ensure_ascii=False);stored=existing.pop(row['id'],None)
            if stored is None:db.add(BattleLog(room_id=room.id,battle_id=battle_id,sequence=row['id'],entry=encoded))
            elif stored.entry!=encoded:stored.entry=encoded
        for stale in existing.values():db.delete(stale)
    if s['phase'] in ('victory','defeat','abandoned'):
        for uid,player_state in s['players'].items():
            points=player_state.get('wongoPointsEarned',0)
            if points and db.get(WongoCredit,(room.id,uid)) is None:
                db.add(WongoCredit(room_id=room.id,user_id=uid,points=points))
            if s['phase']=='victory' and db.get(VictoryCredit,(room.id,uid)) is None:
                db.add(VictoryCredit(room_id=room.id,user_id=uid,character=player_state['character']))

def projection(room,s,uid):
    from sqlalchemy.orm import object_session
    db=object_session(room)
    seat,read_only,grant=control_identity(db,room,uid) if db else (uid,False,None)
    public=view(s,seat)
    public['upgradePreviews']=previews.upgrade_snapshot(s['players'][str(seat)],s)
    if s.get('paused') and s['phase']!='lobby':public['options']=[row for row in public['options'] if row['action'].get('type')!='ready']
    minimum=1 if room.mode=='solo' else 2
    online=sum(key in leases.get(room.id,{}) for key in s['players'])
    public['partyRequirement']={'minimum':minimum,'online':online,'canReady':online>=minimum}
    if online<minimum and (s['phase']=='lobby' or s.get('paused')):
        public['options']=[row for row in public['options'] if row.get('action',{}).get('type')!='ready']
    if read_only:
        public['options']=[]
        public['endTurn']={'canEndTurn':False,'canUndoEndTurn':False,'reason':'存档已托管，当前为旁观模式。'}
    can_sl=not read_only and seat==room.owner_id and (uid==room.owner_id or bool(grant and grant.allow_sl))
    return {**public,'protocol':PROTOCOL_VERSION,'mode':room.mode,'roomId':room.id,'online':list(leases.get(room.id,{})),
        'features':{'roomChat':True,'sl':True,'actionSync':True,'independentChoices':True,'delegation':True},
        'sl':{**sl_status(db,room,s),'canReset':can_sl} if db else {'available':False},'ownerId':room.owner_id,
        'actorId':uid,'readOnly':read_only,'delegation':delegation_view(grant,uid) if grant else None}

def lease_principal(db, room_id, lease):
    seat=lease.seat_uid if lease.seat_uid is not None else lease.uid
    registry=observers if lease.read_only else leases
    key=lease.uid if lease.read_only else seat
    if registry.get(room_id, {}).get(key) is not lease:
        raise SpireApiError(409, 'stale_lease', '游戏连接已更换。')
    principal = authenticate_session(lease.token)
    if principal.user.id != lease.uid:
        raise SpireApiError(401, 'invalid_token', '身份已变化。')
    room,_=principal_room(db, room_id, principal, control=not lease.read_only)
    actual,read_only,grant=control_identity(db,room,lease.uid)
    if actual!=seat or read_only!=lease.read_only or (grant.id if grant else None)!=lease.delegation_id:
        raise SpireApiError(409,'stale_lease','托管授权已变化，请重新连接。')
    return principal


def authorize_delivery(room_id, lease):
    with SessionLocal() as db:
        lease_principal(db, room_id, lease)


async def broadcast(room_id, chat=None, exclude_uid=None):
    for lease in [*leases.get(room_id,{}).values(),*observers.get(room_id,{}).values()]:
        if lease.uid == exclude_uid or (chat is not None and not lease.room_chat):
            continue
        try:
            with SessionLocal() as db:
                principal = lease_principal(db, room_id, lease)
                room, state = principal_room(db, room_id, principal, control=not lease.read_only)
                data = chat if chat is not None else {**projection(room, state, lease.uid), 'leaseId':lease.id}
            if lease.delivery:
                lease.delivery.put(data)
        except HTTPException:
            if lease.delivery:
                await lease.delivery.close_socket(1008)


class CreateRoom(BaseModel):
    model_config=ConfigDict(extra='forbid')
    # Deprecated: rooms are not tied to channels. Accepted and ignored.
    channelId:Id|None=Field(default=None)
    requestId:Id
    seed:str=Field(default='',max_length=64)
    mode:Literal['solo','coop']='coop'
    ascension:int=Field(default=0,ge=0,le=10,strict=True)
    character:Literal['ironclad','silent','defect','regent','necrobinder']='ironclad'
    password:str|None=Field(default=None,pattern=r'^[0-9]{6}$',strict=True,repr=False)
    replaceRoomId:Id|None=None
    replaceRevision:int|None=Field(default=None,ge=0,strict=True)
class JoinRoom(BaseModel):
    model_config=ConfigDict(extra='forbid')
    # New rooms use six digits; rooms created by 0.8.1 may still hold longer passwords.
    password:str|None=Field(default=None,min_length=1,max_length=64,repr=False)
    character:Literal['ironclad','silent','defect','regent','necrobinder']='ironclad'
class Action(BaseModel):
    model_config=ConfigDict(extra='forbid')
    actionId:uuid.UUID
    leaseId:uuid.UUID
    action:dict

def host_online(room):
    return room.owner_id in leases.get(room.id,{})


@router.get('/api/games/spire/catalog')
def catalog_metadata(channelId:Id|None=Query(default=None),principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    authorize_spire(principal)
    return catalog.metadata()


@router.get('/api/games/spire/catalog/{category}')
def catalog_list(category:Literal['cards','monsters','relics','potions','characters'],channelId:Id|None=Query(default=None),
                 q:str=Query(default='',max_length=100),group:str=Query(default='',max_length=100),
                 offset:int=Query(default=0,ge=0),limit:int=Query(default=50,ge=1,le=100),
                 principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    authorize_spire(principal)
    return catalog.listing(category,q,group,offset,limit)


@router.get('/api/games/spire/catalog/{category}/{entry_id}')
def catalog_detail(category:Literal['cards','monsters','relics','potions','characters'],entry_id:str,channelId:Id|None=Query(default=None),
                   ascension:int=Query(default=0,ge=0,le=10),upgraded:bool=False,
                   principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    authorize_spire(principal)
    try:return catalog.detail(category,entry_id,ascension,upgraded)
    except KeyError:raise SpireApiError(404,'entry_not_found','资料条目不存在。')


@router.get('/api/games/spire/rooms')
def list_rooms(channelId:Id|None=Query(default=None),principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    """One site-wide lobby: your own rooms, rooms you play in, and open rooms whose host is online."""
    user=principal.user;authorize_spire(principal)
    result=[]
    invited=select(Delegation.room_id).where(or_(
        and_(Delegation.status=='open',or_(Delegation.invitee_id==None,Delegation.invitee_id==user.id)),
        and_(Delegation.status=='active',Delegation.delegate_id==user.id)))
    recoverable=select(Delegation.room_id).where(Delegation.status.in_(('open','active')))
    query=select(Room).where(or_(Room.finished==0,Room.id.in_(recoverable)),or_(Room.owner_id==user.id,Room.id.in_(list(leases)),Room.id.in_(invited))).order_by(Room.updated_at.desc(),Room.id)
    for room in db.scalars(query):
        if len(result)>=50:break
        grant=current_delegation(db,room.id)
        invited=bool(grant and ((grant.status=='open' and grant.invitee_id in (None,user.id)) or grant.status=='active' and grant.delegate_id==user.id))
        if room.mode=='solo' and room.owner_id!=user.id and not invited:continue
        online=host_online(room)
        if room.mode=='coop' and room.owner_id!=user.id and not online and not invited:continue
        s=json.loads(room.state)
        # Strangers see only rooms that still accept players; started rooms stay with their members.
        if room.mode=='coop' and str(user.id) not in s['players'] and s['phase']!='lobby' and not invited:continue
        result.append({'id':room.id,'ownerId':room.owner_id,'ownerName':s['players'].get(str(room.owner_id),{}).get('name','未知房主'),
            'act':s.get('actIndex',0)+1,'hostOnline':online,'revision':room.revision,'hasPassword':bool(room.password_hash),
            'mode':room.mode,'phase':s['phase'],'paused':s['paused'],'floor':s['floor'],'ascension':s.get('ascension',0),
            'players':[{'id':x['id'],'name':x['name'],'character':x.get('character','ironclad')} for x in s['players'].values()],
            'compatible':s.get('rules')==RULES_VERSION and s.get('content')==CONTENT_VERSION,
            'delegation':delegation_view(grant,user.id) if grant and (invited or room.owner_id==user.id) else None,
            'canClaimDelegation':bool(invited and grant.status=='open' and str(user.id) not in s['players'])})
    return {'protocol':PROTOCOL_VERSION,'features':{'lobby':True,'catalog':True,'hostRecovery':True,'delegation':True,'roomPasswords':True},'phases':list(PHASES),'rooms':result}


@router.post('/api/games/spire/rooms')
async def create_room(body:CreateRoom,principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    user=principal.user;authorize_spire(principal,True);room_id=str(body.requestId)
    original={**body.model_dump(mode='json',exclude={'channelId','password'}),'characterConfigured':'character' in body.model_fields_set}
    if (body.replaceRoomId is None)!=(body.replaceRevision is None) or (body.replaceRoomId and body.mode!='solo'):
        raise SpireApiError(422,'invalid_replacement','替换存档需要单人模式、存档 ID 和版本。')
    if body.password is not None and body.mode!='coop':
        raise SpireApiError(422,'invalid_password','只有多人房间可以设置密码。')
    replaced_id=None
    async with lock_for('create'):
        async with lock_for(str(body.replaceRoomId or room_id)):
            old=db.get(Room,room_id)
            if old:
                saved=json.loads(old.state)
                password_matches=verify_password(body.password,old.password_hash) if body.password is not None else not old.password_hash
                if not password_matches or old.owner_id!=user.id or old.mode!=body.mode or saved.get('ascension',0)!=body.ascension or (saved.get('creationOptions') is not None and saved['creationOptions']!=original):
                    raise SpireApiError(409,'idempotency_conflict','创建请求冲突。')
                return {'id':old.id}
            if body.mode=='solo':
                active=db.scalar(select(Room).where(Room.owner_id==user.id,Room.mode=='solo',Room.finished==0))
                if body.replaceRoomId:
                    if not active or active.id!=str(body.replaceRoomId) or active.revision!=body.replaceRevision:
                        raise SpireApiError(409,'save_changed','存档已变化，请刷新后重新确认。')
                    if current_delegation(db,active.id):raise SpireApiError(409,'control_delegated','请先收回托管再替换存档。')
                    saved=json.loads(active.state)
                    if saved.get('rules')!=RULES_VERSION or saved.get('content')!=CONTENT_VERSION:
                        raise SpireApiError(409,'incompatible_save','旧存档版本不兼容，请先使用对应版本处理。')
                    previous=apply(saved,user.id,{'type':'pause'})
                    previous=apply(previous,user.id,{'type':'abandon'})
                    save(db,active,previous);replaced_id=active.id
                elif active:return {'id':active.id}
            else:
                count=db.scalar(select(func.count()).select_from(Room).where(Room.owner_id==user.id,Room.mode=='coop',Room.finished==0))
                if count>=3:raise SpireApiError(429,'rate_limited','你已有 3 个未结束的合作房间，请先继续或放弃已有房间。')
            s=new_run(body.seed,user.id,user.nickname or user.username,body.mode,body.ascension,body.character)
            s['creationOptions']=original;s['characterConfigured']=original['characterConfigured']
            room=Room(id=room_id,owner_id=user.id,mode=body.mode,password_hash=hash_password(body.password) if body.password is not None else None,state=json.dumps(s,ensure_ascii=False),revision=s['revision'],finished=0)
            db.add(room);db.commit()
    if replaced_id:await broadcast(replaced_id)
    return {'id':room_id}


@router.post('/api/games/spire/rooms/{room_id}/join')
async def join_room(room_id:Id,body:JoinRoom|None=None,principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    user=principal.user
    async with lock_for(room_id):
        room,s=principal_room(db,room_id,principal,False,True)
        if room.finished:raise SpireApiError(409,'room_finished','本局已结束。')
        seat,_,grant=control_identity(db,room,user.id)
        if grant and grant.status=='active' and grant.delegate_id==user.id:return {'id':room_id}
        invitation=current_delegation(db,room_id)
        if invitation and invitation.status=='open' and invitation.invitee_id in (None,user.id) and str(user.id) not in s['players']:
            raise SpireApiError(409,'delegation_pending','请先接受存档托管，不要以新角色加入。')
        if room.mode=='coop' and room.owner_id!=user.id and not host_online(room):
            raise SpireApiError(409,'host_offline','只有房主可以恢复存档，请等待房主进入。')
        if str(user.id) not in s['players']:
            if s['phase']!='lobby' or len(s['players'])>=4:raise SpireApiError(409,'invalid_action','房间已开始或已满。')
            if room.password_hash and not verify_password(body.password if body and body.password is not None else '',room.password_hash):
                raise SpireApiError(403,'invalid_room_password','房间密码错误，请重新输入。')
            s['players'][str(user.id)]=player(s,user.id,user.nickname or user.username,body.character if body else 'ironclad')
            for p in s['players'].values():p['ready']=False
            s['revision']+=1;save(db,room,s);db.commit()
    await broadcast(room_id);return {'id':room_id}


class AbandonRoom(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision:int=Field(ge=0,strict=True)

class OpenDelegation(AbandonRoom):
    requestId:Id
    inviteeId:Id|None=Field(default=None,strict=True)
    allowSl:bool=Field(default=True,strict=True)

class RevokeDelegation(AbandonRoom):
    restoreBefore:bool=Field(default=False,strict=True)

class RestoreDelegation(AbandonRoom):
    requestId:uuid.UUID

@router.post('/api/games/spire/rooms/{room_id}/delegation')
async def open_delegation(room_id:Id,body:OpenDelegation,principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    authorize_spire(principal,True)
    async with lock_for(room_id):
        room,s=member_room(db,room_id,principal.user.id)
        if room.owner_id!=principal.user.id:raise SpireApiError(403,'host_only','只有存档拥有者可以开放代打。')
        existing=db.get(Delegation,str(body.requestId))
        if existing:
            if (existing.room_id,existing.owner_id,existing.invitee_id,bool(existing.allow_sl))!=(room_id,principal.user.id,body.inviteeId,body.allowSl):
                raise SpireApiError(409,'idempotency_conflict','托管请求 ID 已用于其他操作。')
            return delegation_view(existing,principal.user.id)
        if current_delegation(db,room_id):raise SpireApiError(409,'already_delegated','请先收回已有托管。')
        if room.finished:raise SpireApiError(409,'room_finished','已结束的存档不能开始托管。')
        if room.revision!=body.revision:raise SpireApiError(409,'stale_revision','存档已变化，请刷新后确认。')
        if body.inviteeId is not None:
            if str(body.inviteeId) in s['players']:
                raise SpireApiError(422,'invalid_request','代打者须为存档外的有效账号。')
        checkpoints=[{'kind':c.kind,'node':c.node,'battleId':c.battle_id,'snapshot':c.snapshot}
            for c in db.scalars(select(Checkpoint).where(Checkpoint.room_id==room_id))]
        grant=Delegation(id=str(body.requestId),room_id=room_id,owner_id=room.owner_id,invitee_id=body.inviteeId,
            status='open',allow_sl=int(body.allowSl),snapshot=json.dumps(s,ensure_ascii=False),checkpoints=json.dumps(checkpoints))
        db.add(grant)
        s=apply(s,room.owner_id,{'type':'pause'});save(db,room,s);db.commit()
        await close_control(room_id,room.owner_id)
    await broadcast(room_id)
    return delegation_view(grant,principal.user.id)

@router.post('/api/games/spire/rooms/{room_id}/delegation/{grant_id}/claim')
async def claim_delegation(room_id:Id,grant_id:Id,principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    authorize_spire(principal,True)
    async with lock_for(room_id):
        grant=db.get(Delegation,str(grant_id));room=db.get(Room,room_id)
        if not grant or not room or grant.room_id!=room_id or grant.status not in ('open','active'):
            raise SpireApiError(404,'delegation_not_found','托管不存在或已收回。')
        if current_delegation(db,room_id) is not grant:
            raise SpireApiError(409,'stale_delegation','存档或托管版本已变化。')
        if grant.invitee_id not in (None,principal.user.id) or grant.owner_id==principal.user.id:
            raise SpireApiError(403,'delegation_forbidden','此托管未授权给你。')
        s=json.loads(room.state)
        if str(principal.user.id) in s['players']:raise SpireApiError(409,'invalid_action','本局成员不能同时接管另一角色。')
        if grant.status=='active':
            if grant.delegate_id!=principal.user.id:raise SpireApiError(409,'delegation_claimed','已由另一人接管。')
            return delegation_view(grant,principal.user.id)
        if room.finished or s.get('rules')!=RULES_VERSION or s.get('content')!=CONTENT_VERSION:
            raise SpireApiError(409,'incompatible_room','此存档已结束或版本不兼容。')
        grant.delegate_id=principal.user.id;grant.status='active'
        s['revision']+=1;save(db,room,s);db.commit()
    await broadcast(room_id)
    return delegation_view(grant,principal.user.id)

@router.post('/api/games/spire/rooms/{room_id}/delegation/{grant_id}/restore-before')
async def restore_before_delegation(room_id:Id,grant_id:Id,body:RestoreDelegation,principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    authorize_spire(principal,True)
    async with lock_for(room_id):
        room,s=member_room(db,room_id,principal.user.id)
        grant=current_delegation(db,room_id)
        if not grant or grant.id!=str(grant_id) or grant.status!='active':raise SpireApiError(409,'stale_delegation','托管已变化。')
        if principal.user.id!=room.owner_id and not (grant.delegate_id==principal.user.id and grant.allow_sl):
            raise SpireApiError(403,'delegation_forbidden','没有托管前 SL 权限。')
        digest=hashlib.sha256(body.model_dump_json().encode()).hexdigest()
        key=(grant.id,principal.user.id,str(body.requestId));receipt=db.get(DelegationReceipt,key)
        if receipt:
            if receipt.digest!=digest:raise SpireApiError(409,'idempotency_conflict','SL 请求 ID 已用于其他操作。')
            return {'state':projection(room,s,principal.user.id),'restored':True}
        if room.revision!=body.revision:raise SpireApiError(409,'stale_revision','存档已变化，请刷新后确认。')
        s=restore_delegation_snapshot(db,room,grant)
        db.add(DelegationReceipt(delegation_id=grant.id,actor_id=principal.user.id,request_id=str(body.requestId),digest=digest));db.commit()
        await close_control(room_id)
    await broadcast(room_id)
    return {'state':projection(room,s,principal.user.id),'restored':True}

@router.post('/api/games/spire/rooms/{room_id}/delegation/{grant_id}/revoke')
async def revoke_delegation(room_id:Id,grant_id:Id,body:RevokeDelegation,principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    authorize_spire(principal,True)
    async with lock_for(room_id):
        room,s=member_room(db,room_id,principal.user.id)
        if room.owner_id!=principal.user.id:raise SpireApiError(403,'host_only','只有存档拥有者可以收回托管。')
        grant=db.get(Delegation,str(grant_id))
        if not grant or grant.room_id!=room_id:raise SpireApiError(404,'delegation_not_found','托管不存在。')
        if grant.status=='revoked':
            if bool(grant.revoke_restore)!=body.restoreBefore:raise SpireApiError(409,'idempotency_conflict','此托管已按另一方式收回。')
            return {'state':projection(room,s,principal.user.id),'restored':bool(grant.revoke_restore)}
        if current_delegation(db,room_id) is not grant or room.revision!=body.revision:
            raise SpireApiError(409,'stale_revision','托管或存档已变化，请刷新。')
        if body.restoreBefore:s=restore_delegation_snapshot(db,room,grant)
        else:s=apply(s,room.owner_id,{'type':'pause'});save(db,room,s)
        grant.status='revoked';grant.revoke_restore=int(body.restoreBefore);db.commit()
        await close_control(room_id,None if body.restoreBefore else room.owner_id,include_observers=True)
    await broadcast(room_id)
    return {'state':projection(room,s,principal.user.id),'restored':body.restoreBefore}

@router.post('/api/games/spire/rooms/{room_id}/abandon')
async def abandon_room(room_id:Id,body:AbandonRoom,principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    async with lock_for(room_id):
        room,s=principal_room(db,room_id,principal,control=True)
        if room.owner_id!=principal.user.id:raise SpireApiError(403,'host_only','只有房主可以放弃本局。')
        if s['phase']=='abandoned':return {'id':room_id}
        if room.finished:raise SpireApiError(409,'room_finished','本局已结束。')
        if room.revision!=body.revision:raise SpireApiError(409,'stale_revision','存档已变化，请刷新后再放弃。')
        s=apply(s,principal.user.id,{'type':'abandon'});save(db,room,s);db.commit()
    await broadcast(room_id)
    return {'id':room_id}

@router.get('/api/games/spire/rooms/{room_id}')
def get_room(room_id:Id,principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    room,s=principal_room(db,room_id,principal);return projection(room,s,principal.user.id)

@router.get('/api/games/spire/rooms/{room_id}/logs')
def battle_logs(room_id:Id,battleId:int|None=Query(default=None,ge=1),
                before:int|None=Query(default=None,ge=1),after:int|None=Query(default=None,ge=0),
                limit:int=Query(default=100,ge=1,le=200),
                principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    user=principal.user;room,s=principal_room(db,room_id,principal)
    seat,_,_=control_identity(db,room,user.id)
    battle_log.legacy(s)
    current=s.get('battleId')
    if battleId is not None and battleId!=current:raise SpireApiError(409,'stale_phase','战斗已更换，请刷新日志。')
    if before is not None and after is not None:raise SpireApiError(400,'invalid_request','只能指定一个分页游标。')
    query=select(BattleLog).where(BattleLog.room_id==room.id,BattleLog.battle_id==current)
    if before is not None:query=query.where(BattleLog.sequence<before)
    if after is not None:query=query.where(BattleLog.sequence>after)
    query=query.order_by(BattleLog.sequence.desc() if before is not None else BattleLog.sequence).limit(limit)
    records=[json.loads(row.entry) for row in db.scalars(query)]
    if before is not None:records.reverse()
    if not db.scalar(select(BattleLog.sequence).where(BattleLog.room_id==room.id).limit(1)):
        records=[row for row in s.get('log',[]) if (before is None or row['id']<before) and (after is None or row['id']>after)]
        records=records[-limit:] if before is not None else records[:limit]
    meta=battle_log.metadata(s)
    return {**meta,'entries':[battle_log.project(row,seat) for row in records],
            'before':records[0]['id'] if records and records[0]['id']>1 else None,
            'after':records[-1]['id'] if records and records[-1]['id']<(meta['last'] or 0) else None}

@router.get('/api/games/spire/rooms/{room_id}/players/{player_id}/inspection')
def inspect_player(room_id:Id,player_id:Id,page:int=0,size:int=previews.INSPECTION_PAGE_SIZE,
                   principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    """Read-only, paged view of one player. No lease, no receipt, no write.

    It reads straight from the stored state rather than taking the room lock:
    nothing here can change the state, so there is nothing to serialise.
    """
    room,s=principal_room(db,room_id,principal)
    target=s['players'].get(str(player_id))
    if target is None:raise SpireApiError(404,'player_not_found','玩家不在此房间。')
    try:
        header=previews.inspection(target)
        header['page']=page
        header['rows']=previews.page(header['rows'],page,size)
        header['pageSize']=size
    except InvalidAction as error:raise SpireApiError(400,'invalid_request',str(error))
    return header

def prepare_action(db, room_id, body, principal, timing):
    """Validate and compute. The caller owns the transaction and room lock."""
    user = principal.user
    if len(json.dumps(body.action).encode()) > 8192:
        raise SpireApiError(413, 'action_too_large', '操作过大。')
    digest = hashlib.sha256(json.dumps(body.action, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    with timing.span('load'):
        room, state = principal_room(db, room_id, principal, control=True)
        seat,_,_=control_identity(db,room,user.id,True)
        receipt = db.scalar(select(Receipt).where(
            Receipt.room_id == room_id, Receipt.user_id == user.id,
            Receipt.action_id == str(body.actionId)))
    if receipt:
        if receipt.digest != digest:
            raise SpireApiError(409, 'idempotency_conflict', '操作 ID 已用于其他操作。')
        return room, state, digest, True
    lease = lease_for(room_id,seat,user.id)
    if lease is None or lease.id != str(body.leaseId):
        raise SpireApiError(409, 'stale_lease', '游戏连接已更换，请等待重新连接。')
    now = time.monotonic()
    lease.actions = [stamp for stamp in lease.actions if now-stamp < 1]
    if len(lease.actions) >= 12:
        raise SpireApiError(429, 'rate_limited', '操作过快，请稍后重试。', True)
    lease.actions.append(now)
    if body.action.get('type') == 'abandon' and room.owner_id != user.id:
        raise SpireApiError(403, 'host_only', '只有房主可以放弃本局。')
    if body.action.get('type') == 'ready':
        online = sum(key in leases.get(room_id, {}) for key in state['players'])
        if room.mode == 'coop' and online < 2:
            raise SpireApiError(409, 'insufficient_players', '多人模式至少需要 2 名在线玩家。')
        if (all(p['ready'] or p['id'] == seat for p in state['players'].values())
                and any(p['id'] not in leases.get(room_id, {}) for p in state['players'].values())):
            raise SpireApiError(409, 'invalid_action', '等待其他玩家重新进入游戏。')
    with timing.span('progress'):
        load_progress(db, state)
    try:
        with timing.span('rules'):
            state = apply(state, seat, body.action)
    except (InvalidAction, KeyError, TypeError) as error:
        message = str(error) if isinstance(error, InvalidAction) else '操作格式无效。'
        raise SpireApiError(409, 'stale_phase' if '阶段已变化' in message else 'invalid_action', message)
    return room, state, digest, False


def persist_action(db, room, state, body, uid, digest, timing):
    with timing.span('save'):
        save(db, room, state)
        db.add(Receipt(id=new_id(), room_id=room.id, user_id=uid,
                       action_id=str(body.actionId), digest=digest))
        db.flush()
        db.expire(room)


def chain_boundary(before, after):
    return (before.get('phaseId') != after.get('phaseId')
            or before.get('turn') != after.get('turn')
            or after.get('paused')
            or after.get('pendingChoice') or after.get('pendingDecision')
            or after.get('phase') in ('victory', 'defeat', 'abandoned'))


def api_error(error):
    return {'status':error.status_code, 'code':getattr(error, 'code', 'request_failed'),
            'message':str(error.detail), 'retryable':getattr(error, 'retryable', False)}


async def perform_action(room_id, body, principal, db, timing, receipt_only=False, control_lease=None):
    lock = lock_for(room_id)
    with timing.span('lock'):
        await lock.acquire()
    try:
        if control_lease is not None:
            lease_principal(db, room_id, control_lease)
        _, before = principal_room(db, room_id, principal, control=True)
        if receipt_only and not db.scalar(select(Receipt).where(Receipt.room_id == room_id, Receipt.user_id == principal.user.id, Receipt.action_id == str(body.actionId))):
            raise SpireApiError(409, "action_not_committed", "动作未提交，请根据最新状态重新操作。")
        room, state, digest, duplicate = prepare_action(db, room_id, body, principal, timing)
        if not duplicate:
            persist_action(db, room, state, body, principal.user.id, digest, timing)
            with timing.span('commit'):
                db.commit()
        with timing.span('projection'):
            snapshot = projection(room, state, principal.user.id)
        return snapshot, duplicate or bool(chain_boundary(before, state))
    finally:
        lock.release()


def timed_response(payload, timing, dependency_response):
    with timing.span('serialize'):
        response = JSONResponse(payload)
    response.raw_headers.extend((key, value) for key, value in dependency_response.raw_headers
                                if key.lower() not in (b'content-length', b'content-type'))
    response.headers['Server-Timing'] = timing.header()
    return response


@router.post('/api/games/spire/rooms/{room_id}/actions')
async def action(room_id:Id, body:Action, response:Response, background_tasks:BackgroundTasks,
                 receiptOnly:bool=False,
                 principal:SpirePrincipal=Depends(spire_identity), db:Session=Depends(get_db)):
    timing = Timing(body.actionId)
    try:
        snapshot, _ = await perform_action(room_id, body, principal, db, timing, receiptOnly)
        if not receiptOnly:
            background_tasks.add_task(broadcast, room_id, exclude_uid=principal.user.id)
        reply = timed_response(snapshot, timing, response)
        timing.log('ok')
        return reply
    except HTTPException:
        timing.log('rejected')
        raise


class BatchItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    actionId: uuid.UUID
    action: dict


class ActionBatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    batchId: uuid.UUID
    leaseId: uuid.UUID
    actions: list[BatchItem] = Field(min_length=1, max_length=8)


@router.post('/api/games/spire/rooms/{room_id}/actions/batch')
async def action_batch(room_id:Id, body:ActionBatch, response:Response, background_tasks:BackgroundTasks,
                       principal:SpirePrincipal=Depends(spire_identity), db:Session=Depends(get_db)):
    if len({item.actionId for item in body.actions}) != len(body.actions):
        raise SpireApiError(422, 'invalid_request', '批量动作 ID 不得重复。')
    encoded = json.dumps([item.model_dump(mode='json') for item in body.actions], sort_keys=True, separators=(',', ':'))
    if len(encoded.encode()) > 65536:
        raise SpireApiError(413, 'action_too_large', '操作过大。')
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    timing = Timing(body.batchId)
    lock = lock_for(room_id)
    with timing.span('lock'):
        await lock.acquire()
    try:
        room, state = principal_room(db, room_id, principal, control=True)
        receipt = db.get(BatchReceipt, (room_id, principal.user.id, str(body.batchId)))
        if receipt:
            if receipt.digest != digest:
                raise SpireApiError(409, 'idempotency_conflict', '批量 ID 已用于其他操作。')
            result = json.loads(receipt.result)
        else:
            result = {'batchId':str(body.batchId), 'results':[], 'stopped':None}
            for index, item in enumerate(body.actions):
                action_body = Action(actionId=item.actionId, leaseId=body.leaseId, action=item.action)
                before = state
                try:
                    room, next_state, action_digest, duplicate = prepare_action(
                        db, room_id, action_body, principal, timing)
                except HTTPException as error:
                    result['stopped'] = {'index':index, 'actionId':str(item.actionId), 'error':api_error(error)}
                    break
                if not duplicate:
                    persist_action(db, room, next_state, action_body, principal.user.id, action_digest, timing)
                state = next_state
                result['results'].append({'actionId':str(item.actionId), 'revision':state['revision'], 'duplicate':duplicate})
                if duplicate or chain_boundary(before, state):
                    if index+1 < len(body.actions):
                        result['stopped'] = {'index':index+1, 'reason':'decision_boundary'}
                    break
            db.add(BatchReceipt(room_id=room_id, user_id=principal.user.id, batch_id=str(body.batchId),
                                digest=digest, result=json.dumps(result)))
            with timing.span('commit'):
                db.commit()
        with timing.span('projection'):
            snapshot = projection(room, state, principal.user.id)
        background_tasks.add_task(broadcast, room_id, exclude_uid=principal.user.id)
        reply = timed_response({**result, 'state':snapshot, 'timing':timing.snapshot()}, timing, response)
        timing.log('batch')
        return reply
    finally:
        lock.release()


class SocketAction(Action):
    type: Literal['ACTION']
    afterActionId: uuid.UUID | None = None


class SocketSync(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['SYNC']
    requestId: uuid.UUID
    leaseId: uuid.UUID
    actionIds: list[uuid.UUID] = Field(max_length=8)


async def socket_sync(room_id, lease, message):
    body = SocketSync.model_validate_json(message)
    timing = Timing(body.requestId)
    async with lock_for(room_id):
        with SessionLocal() as db:
            principal = lease_principal(db, room_id, lease)
            if lease.read_only or lease_for(room_id,lease.seat_uid if lease.seat_uid is not None else lease.uid,lease.uid) is not lease or str(body.leaseId) != lease.id:
                raise SpireApiError(409, 'stale_lease', '游戏连接已更换。')
            room, state = principal_room(db, room_id, principal, control=True)
            results = [{'actionId': str(ident), 'status': 'committed' if db.scalar(select(Receipt).where(
                Receipt.room_id == room_id, Receipt.user_id == lease.uid,
                Receipt.action_id == str(ident))) else 'not_committed'} for ident in body.actionIds]
            lease.delivery.put({'type': 'SYNC_RESULT', 'requestId': str(body.requestId),
                                'leaseId': lease.id, 'results': results,
                                'state': {**projection(room, state, lease.uid), 'leaseId': lease.id}}, str(body.requestId))
            logger.info('spire_sync request_id=%s lease_id=%s results=%s timing_ms=%s',
                        body.requestId, lease.id, results, timing.snapshot())


async def socket_action(room_id, lease, message):
    try:
        body = SocketAction.model_validate_json(message)
    except ValidationError as error:
        reason = '; '.join('.'.join(map(str, item['loc'])) + ': ' + item['msg'] for item in error.errors(include_input=False))
        lease.follow_allowed = False
        try:
            ident = str(uuid.UUID(json.loads(message).get('actionId', '')))
        except (ValueError, TypeError, AttributeError):
            ident = None
        lease.delivery.put({'type':'ACTION_ERROR', 'actionId':ident,
                            'error':{'status':422, 'code':'invalid_request', 'message':'动作格式无效：' + reason}})
        return
    timing = Timing(body.actionId)
    logger.info('spire_receive action_id=%s lease_id=%s bytes=%s', body.actionId, lease.id, len(message.encode()))
    try:
        with SessionLocal() as db:
            principal = lease_principal(db, room_id, lease)
            if str(body.leaseId) != lease.id:
                raise SpireApiError(409, 'stale_lease', '游戏连接已更换。')
            if body.afterActionId is not None and (
                    str(body.afterActionId) != lease.last_action_id or not lease.follow_allowed):
                raise SpireApiError(409, 'queue_stopped', '前序动作失败或需要新选择，后续动作已停止。')
            snapshot, boundary = await perform_action(room_id, body, principal, db, timing, control_lease=lease)
        lease.last_action_id = str(body.actionId)
        lease.follow_allowed = not boundary
        lease.delivery.put({'type':'ACTION_RESULT', 'actionId':str(body.actionId),
                            'state':{**snapshot, 'leaseId':lease.id}, 'timing':timing.snapshot(),
                            'stopQueue':boundary}, str(body.actionId))
        timing.log('ok')
        await asyncio.sleep(0)
        await broadcast(room_id, exclude_uid=lease.uid)
    except HTTPException as error:
        lease.follow_allowed = False
        lease.delivery.put({'type':'ACTION_ERROR', 'actionId':str(body.actionId),
                            'error':api_error(error), 'timing':timing.snapshot()}, str(body.actionId))
        logger.info('spire_rejected action_id=%s status=%s code=%s', body.actionId, error.status_code, api_error(error).get('code'))
        timing.log('rejected')
    except Exception:
        lease.follow_allowed = False
        lease.delivery.put({'type':'ACTION_ERROR', 'actionId':str(body.actionId),
                            'error':{'status':503, 'code':'spire_unavailable',
                                     'message':'结果待确认，请在当前连接核对动作结果。', 'retryable':True}},
                           str(body.actionId))
        timing.log('unknown')

class RoomChat(BaseModel):
    model_config=ConfigDict(extra='forbid')
    messageId:uuid.UUID
    leaseId:uuid.UUID
    content:str=Field(min_length=1,max_length=200,strict=True)
    scopeToken:uuid.UUID|None=None

async def reset_scene(room_id,body,principal,db):
    uid=principal.user.id;ident=str(body.messageId)
    async with lock_for(room_id):
        room,s=principal_room(db,room_id,principal,control=True)
        seat,_,grant=control_identity(db,room,uid,True)
        lease=lease_for(room_id,seat,uid)
        if lease is None or lease.id!=str(body.leaseId):raise SpireApiError(409,'stale_lease','游戏连接已更换，请等待重新连接。')
        if seat!=room.owner_id or grant and uid!=room.owner_id and not grant.allow_sl:
            raise SpireApiError(403,'host_only','此账号没有当前存档的 SL 权限。')
        prior=db.get(ResetReceipt,(room_id,uid,ident))
        if prior:
            if prior.token!=str(body.scopeToken):raise SpireApiError(409,'idempotency_conflict','SL 请求 ID 已用于其他节点。')
            return json.loads(prior.event)
        status=sl_status(db,room,s)
        if not status['available']:raise SpireApiError(409,'sl_unavailable','当前场景没有可用的初始存档点，或游戏已暂停、结束。')
        if str(body.scopeToken)!=status['token']:raise SpireApiError(409,'stale_checkpoint','节点或阶段已变化，请重新打开聊天输入 /sl。')
        entry=scene_checkpoint(db,room,s)
        reset=json.loads(entry.snapshot)
        from .core.continuation import rebase_phase
        rebase_phase(reset,s['phaseId']+1-reset['phaseId'])
        reset['revision']=s['revision']+1;reset['paused']=False
        load_progress(db,reset)
        # A delayed request cannot reset this scene a second time.
        for checkpoint in db.scalars(select(Checkpoint).where(Checkpoint.room_id==room_id)):
            checkpoint.token=new_id()
        save(db,room,reset)
        message='SL 完成，已恢复当前场景初始状态。'
        event={'type':'ROOM_CHAT','id':ident,'roomId':room_id,'userId':uid,
               'name':principal.user.nickname or principal.user.username,'content':message,
               'createdAt':datetime.now(timezone.utc).isoformat(),'command':'sl','restored':True}
        db.add(ResetReceipt(room_id=room_id,user_id=uid,message_id=ident,token=str(body.scopeToken),event=json.dumps(event,ensure_ascii=False)))
        db.commit()
    await broadcast(room_id)
    await broadcast(room_id,event)
    return event


@router.post('/api/games/spire/rooms/{room_id}/chat')
async def room_chat(room_id:Id,body:RoomChat,principal:SpirePrincipal=Depends(spire_identity),db:Session=Depends(get_db)):
    # Ephemeral transport, deliberately outside apply/save and the action budget.
    content=' '.join(body.content.split())
    if not content or any(ord(c)<32 or 127<=ord(c)<=159 or c in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069' for c in content):
        raise SpireApiError(422,'validation_error','请输入不含控制字符的消息。')
    if content=='/sl':return await reset_scene(room_id,body,principal,db)
    uid=principal.user.id
    async with lock_for('chat:'+room_id):
        room,s=principal_room(db,room_id,principal)
        authorize_spire(principal,True)
        seat,read_only,_=control_identity(db,room,uid)
        lease=observers.get(room_id,{}).get(uid) if read_only else lease_for(room_id,seat,uid)
        if lease is None or lease.id!=str(body.leaseId):
            raise SpireApiError(409,'stale_lease','游戏连接已更换，请等待重新连接。')
        now=time.monotonic()
        lease.chat_receipts={key:value for key,value in lease.chat_receipts.items() if now-value[0]<60}
        ident=str(body.messageId)
        prior=lease.chat_receipts.get(ident)
        if prior:
            if prior[1]['content']!=content:
                raise SpireApiError(409,'idempotency_conflict','消息 ID 已用于其他内容。')
            return prior[1]
        lease.chat_times=[t for t in lease.chat_times if now-t<10]
        if len(lease.chat_times)>=5:
            raise SpireApiError(429,'rate_limited','每 10 秒最多发送 5 条消息，请稍后重试。',True)
        lease.chat_times.append(now)
        event={'type':'ROOM_CHAT','id':ident,'roomId':room_id,'userId':uid,
               'name':principal.user.nickname or principal.user.username,'content':content,
               'createdAt':datetime.now(timezone.utc).isoformat()}
        lease.chat_receipts[ident]=(now,event)
        await broadcast(room_id,event)
        return event

@router.websocket('/ws/games/spire/rooms/{room_id}')
async def room_socket(ws:WebSocket,room_id:Id):
    origin=ws.headers.get('origin')
    if origin:
        parsed=urlsplit(origin)
        if parsed.scheme not in ('http','https') or parsed.netloc!=ws.headers.get('host') or parsed.username:
            await ws.close(code=1008);return
    bearer=_bearer_token(ws.headers.get('authorization'))
    auth_kind='bearer' if bearer else 'cookie'
    token=bearer or ws.cookies.get(COOKIE_NAME)
    if 'linkchat-game-v8' not in ws.headers.get('sec-websocket-protocol','').split(', '):await ws.close(code=1008);return
    try:
        with SessionLocal() as db:
            principal=authenticate_session(token);uid=principal.user.id
            room,_=principal_room(db,room_id,principal)
            seat,read_only,grant=control_identity(db,room,uid)
            authorize_spire(principal,not read_only)
    except HTTPException:await ws.close(code=1008);return
    await ws.accept(subprotocol='linkchat-game-v8');lease=Lease(ws,uid,token,auth_kind,seat_uid=seat,read_only=read_only,
        delegation_id=grant.id if grant else None,room_chat=ws.query_params.get('roomChat')=='1')
    async with lock_for(room_id):
        with SessionLocal() as db:
            room=db.get(Room,room_id)
            current_seat,current_read_only,current_grant=control_identity(db,room,uid)
            if (current_seat,current_read_only,current_grant.id if current_grant else None)!=(seat,read_only,lease.delegation_id):
                await ws.close(code=4001);return
            if room.mode=='coop' and room.owner_id!=seat and not host_online(room):
                await ws.close(code=1008);return
        registry=observers if read_only else leases
        registry_key=uid if read_only else seat
        old=registry.setdefault(room_id,{}).get(registry_key);registry[room_id][registry_key]=lease
    lease.delivery = Delivery(ws, lambda: authorize_delivery(room_id, lease), lease.send_lock)
    if old:
        try:await old.ws.close(code=4001)
        except (RuntimeError,OSError):pass
    try:
        async with lock_for(room_id):
            with SessionLocal() as db:
                room=db.get(Room,room_id);s=json.loads(room.state)
                # Existing runs resume once every original controller is connected.
                if not read_only and not room.finished and s.get('paused') and s['phase']!='lobby' and len(s['players'])>=(1 if room.mode=='solo' else 2) and all(key in leases.get(room_id,{}) for key in s['players']):
                    load_progress(db,s)
                    for key in s['players']:
                        if not s['paused']:break
                        s=apply(s,key,{'type':'ready'})
                    save(db,room,s);db.commit()
        await broadcast(room_id)
        while True:
            message=await asyncio.wait_for(ws.receive_text(),45)
            if message != 'PING':
                if len(message.encode()) <= 4 * 1024 * 1024:
                    try:
                        payload = json.loads(message)
                        if isinstance(payload, dict) and payload.get('type') == 'SYNC':
                            await socket_sync(room_id, lease, message)
                        else:
                            await socket_action(room_id, lease, message)
                    except (ValidationError, ValueError, HTTPException) as error:
                        lease.delivery.put({'type':'ACTION_ERROR', 'actionId':None,
                                            'error':{'status':422, 'code':'invalid_request', 'message':'同步请求无效或连接已更换。'}})
                    continue
                await ws.close(code=1009)
                break
            with SessionLocal() as db:
                lease_principal(db,room_id,lease)
            lease.delivery.put('PONG')
    except HTTPException:
        # The socket has already been accepted, so returning from the ASGI app
        # alone does not give clients a close frame.  Authentication can change
        # while a connection is alive (for example when a Spire token is
        # revoked), and the next heartbeat must terminate it deterministically.
        try:await ws.close(code=1008)
        except (RuntimeError,OSError):pass
    except WebSocketDisconnect as error:
        logger.info('spire_disconnect lease_id=%s code=%s', lease.id, error.code)
    except (asyncio.TimeoutError, RuntimeError, OSError):
        await lease.delivery.close_socket(1011)
    except asyncio.CancelledError:
        raise
    finally:
        with CancelScope(shield=True):
            await lease.delivery.stop()
            async with lock_for(room_id):
                active=registry.get(room_id,{})
                if active.get(registry_key) is lease:
                    del active[registry_key]
                    if not active:registry.pop(room_id,None)
                    with SessionLocal() as db:
                        room=db.get(Room,room_id)
                        if room and not read_only:
                            s=json.loads(room.state)
                            if s.get('rules')==RULES_VERSION and s.get('content')==CONTENT_VERSION:
                                s=apply(s,seat,{'type':'pause'});save(db,room,s);db.commit()
            await broadcast(room_id)
