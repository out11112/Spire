"""Run state: creating runs and players, the log and phase, cards and rewards in the deck."""
from ..text import battle_log
from copy import deepcopy
from decimal import Decimal
from ..content import CARDS, RELICS, RULES_VERSION, CONTENT_VERSION, SCHEMA_VERSION, PHASES, definition
from ..content.characters import CHARACTERS
from .errors import require
from ..combat import damage

def log(s, message):
    battle_log.emit(s,message)

def phase(s, value):
    require(value in PHASES, '未知阶段：' + str(value))
    if s.get('phase')=='combat' and value!='combat':
        battle_log.emit(s,'战斗结算：'+value,'outcome')
        s['battleLogging']=False
        for p in s['players'].values():p.pop('relicCombat',None)
    s['phase']=value; s['phaseId']+=1
    for p in s['players'].values(): p['done']=False

def new_card(s,key,upgraded=False):
    s['serial']+=1
    return {'id':str(s['serial']), 'key':key, 'upgraded':upgraded}

def gain_gold(s,p,amount,*,stolen_back=False):
    if 'Ectoplasm' in p['relics']:return 0
    amount=Decimal(str(amount))
    if 'BowlerHat' in p['relics']:amount*=Decimal('1.25')
    if amount<=0:return 0
    gained=int(amount);p['gold']+=gained
    if not stolen_back:p['scoreGoldGained']=p.get('scoreGoldGained',0)+gained
    if 'DragonFruit' in p['relics']:p['maxHp']+=1;damage.heal(p,1)
    return gained

def obtain_card(s,p,card,*,cloned_by=None):
    from ..relics.hooks import modify_acquired_card
    modify_acquired_card(p,card);p['deck'].append(card)
    from ..relics.hooks import card_added
    card_added(s,p,card,cloned_by=cloned_by)
    return card

def ensure_player_seats(s):
    """Upgrade pre-seat saves by their stable room insertion order."""
    players=list(s.get('players',{}).values())
    used={row.get('seat') for row in players if isinstance(row.get('seat'),int) and row['seat']>=0}
    free=(index for index in range(4) if index not in used)
    for row in players:
        if not isinstance(row.get('seat'),int) or row['seat']<0:row['seat']=next(free)

def player(s,uid,name,character='ironclad',seat=None):
    require(character in CHARACTERS,'未知职业。');config=CHARACTERS[character]
    ensure_player_seats(s)
    if seat is None and str(uid) in s.get('players',{}):seat=s['players'][str(uid)].get('seat')
    if seat is None:
        used={row.get('seat') for row in s.get('players',{}).values() if isinstance(row.get('seat'),int)}
        seat=next(index for index in range(4) if index not in used)
    require(isinstance(seat,int) and 0<=seat<4,'无效的玩家席位。')
    result={'id':uid,'seat':seat,'name':name,'character':character,'hp':config['hp'],'maxHp':config['hp'],'gold':config['gold'],'block':0,'energy':0,'powers':{},'deck':[new_card(s,k) for k in config['deck']], 'relics':list(config['relics']),'potions':[], 'pendingPotions':[], 'hand':[],'draw':[],'discard':[],'exhaust':[], 'ready':False,'done':False,'flower':0,'vote':None,'removeCost':100 if s.get('ascension',0)>=6 else 75}
    result['ascension']=s.get('ascension',0)
    if result['ascension']>=4:result['potionCapacity']=2
    if result['ascension']>=5:result['deck'].append(new_card(s,'AscendersBane'))
    return result

def new_run(seed,uid,name,mode='coop',ascension=0,character='ironclad'):
    require(type(ascension) is int and 0<=ascension<=10,'进阶等级必须为 A0–A10。')
    require(mode in ('solo','coop'),'无效的游戏模式。')
    from ..rng.mega_random import canonicalize_seed, generate_seed
    # A blank seed is generated here rather than derived from anything about the
    # room or the account, so the reported seed alone reproduces the run.
    seed=canonicalize_seed(seed) or generate_seed()
    # No ``rng`` key: the run's randomness lives in ``streams``, one entry per
    # named lane, and a second home for it would be a second thing to keep true.
    s={'schema':SCHEMA_VERSION,'rules':RULES_VERSION,'content':CONTENT_VERSION,'seed':seed,'serial':0,'phase':'lobby','phaseId':1,'revision':0,'paused':False,'floor':0,'turn':0,'players':{},'enemies':[],'map':[],'log':[],'event':None}
    s['mode']=mode;s['ascension']=ascension
    s['players'][str(uid)]=player(s,uid,name,character)
    if mode=='solo':
        from ..run.map.journey import initialize
        initialize(s,False);phase(s,'map')
    return s

def relic(s,p,key):
    require(key in RELICS,'遗物效果尚未实现：'+key)
    if key in p['relics']+p.get('meltedRelics',[]) and key!='Circlet':return
    p['relics'].append(key)
    from ..relics.pool import obtained as bag_obtained
    bag_obtained(s,p,key)
    if key=='HappyFlower':p['flower']=0
    if key=='Strawberry':p['maxHp']+=7;damage.heal(p,7)
    if key=='Byrdpip':
        from ..run.map.quests import byrdpip_obtained
        byrdpip_obtained(s,p)
    from ..relics.hooks import obtained
    obtained(s,p,key)
    log(s,f"{p['name']} 获得 {RELICS[key][0]}")

def random_relic(s,p):
    from ..relics.pool import pull
    relic(s,p,pull(s,p))

def potion_reward(s,p,n=1):
    from ..run.potions import reward
    reward(s,p,n)

def find_card(cards,ident):
    value=next((c for c in cards if c['id']==ident),None)
    require(value is not None,'这张牌已不在原处，请重新选择。');return value

def upgradable(c): return not c.get('upgraded') and CARDS[c['key']]['kind'] not in ('status','curse','quest')

def upgrade(c):
    if not upgradable(c):return
    base=CARDS[c['key']];change=base['upgrade'].get('cost',0)
    if change<0 and not base['values'].get('xCost'):
        from ..combat.costs import legacy
        c.setdefault('costModifiers',legacy(c))
        maximum=max(0,base['cost']+change)
        for row in c['costModifiers']:
            if row['mode']=='set':row['amount']=min(row['amount'],maximum)
    c['upgraded']=True

def downgrade(c):
    c['upgraded']=False
    c.pop('addedKeywords',None);c.pop('removedKeywords',None)
    c.pop('baseCostAdjustment',None)
    from ..combat.enchantments import modify_card
    modify_card(c)

def removable(c): return not definition(c)['values'].get('eternal')

def copy_card(s,c):
    if c['key']=='SovereignBlade' and 'swordSageReplays' not in c:
        from ..combat.classes.regent import owned_blades, prepare_blade
        for owner in s['players'].values():
            if any(blade['id']==c['id'] for blade in owned_blades(owner)):
                prepare_blade(owner,c);break
    copied=deepcopy(c);copied['id']=new_card(s,c['key'])['id']
    if definition(c)['values'].get('pinpoint'):copied['pinpointClone']=True
    if definition(c)['values'].get('stomp'):copied['stompClone']=True
    if definition(c)['values'].get('midnight'):copied['midnightClone']=True
    if copied['key']=='SovereignBlade':copied.setdefault('swordSageReplays',0)
    copied.pop('appliedDebuffs',None);copied.pop('relicAutoPlay',None)
    for key in ('capturedX','capturedStars','priorTargetHits','forgeAttackResults','replayTarget','replaysLeft','nostalgiaReturn','passTo','calamityCount','strangleDamage','forceExhaust'):copied.pop(key,None)
    for key in ('copiedDebuffs','attackDamage','resourceEnergyValue','afterimageBlock','serpentDamage'):copied.pop(key,None)
    for key in ('stormOrbs','subroutineEnergy','imitationCopies','paidEnergy','feralReturn'):copied.pop(key,None)
    copied.pop('seriesStarsSpent',None)
    copied.pop('monologueStrength',None)
    copied.pop('monologueSnapshots',None)
    copied.pop('manualSeries',None)
    copied.pop('oblivionDoom',None);copied.pop('lethalityPercent',None)
    return copied
