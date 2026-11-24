"""Persistent quest-card effects. Map helpers are used by three-act navigation."""
from ... import engine as e


def has(state,key):return any(c['key']==key for p in state.get('players',{}).values() for c in p.get('deck',[]))


def hatch(state,player):
    e.require(any(c['key']=='ByrdonisEgg' for c in player['deck']),'没有可孵化的蛋。')
    e.relic(state,player,'Byrdpip')


def byrdpip_obtained(state,player):
    from ..events.transforms import replace_in_pile
    for pile in ('deck','hand','draw','discard','exhaust','inPlay'):
        for card in list(player.get(pile,[])):
            if card['key']=='ByrdonisEgg':replace_in_pile(state,player,player[pile],card,e.new_card(state,'ByrdSwoop'))
    e.log(state,f"{player['name']} 的蛋孵化为异鸟宝宝，任务牌变为飞鸟俯冲")


def room_entered(state,room):
    from ..events.transforms import replace_in_pile
    if room.get('subroom'):return
    for player in state.get('players',{}).values():
        for card in list(player.get('deck',[])):
            if card['key']=='Dowsing' and room.get('mapKind',room['kind'])=='unknown':
                card['questRooms']=card.get('questRooms',0)+1
                if card['questRooms']>=5:
                    replace_in_pile(state,player,player['deck'],card,e.new_card(state,'Abundance'))
                    e.log(state,f"{player['name']} 完成探寻，获得丰饶")


def bind_spoils(state,graph,act_index):
    """Bind against the final map in reference column/row traversal order."""
    nodes=sorted(graph['nodes'].values(),key=lambda node:(node['col'],node['row']))
    target=next((node['id'] for node in nodes if node['kind']=='treasure'),None)
    for player in state.get('players',{}).values():
        for card in player.get('deck',[]):
            if card['key']=='SpoilsMap' and card.get('spoilsActIndex',1)==act_index:
                card['spoilsNodeId']=target


def treasure_reward(state,player):
    """Called only after this player's treasure eligibility and ordinary gold."""
    room=state.get('node',{})
    if room.get('kind')!='treasure' or room.get('mapKind',room['kind'])!='treasure':return
    for card in list(player.get('deck',[])):
        if (card['key']=='SpoilsMap' and card.get('spoilsNodeId') is not None
                and room.get('id')==card['spoilsNodeId']
                and room.get('actIndex',state.get('actIndex',0))==card.get('spoilsActIndex',1)):
            e.gain_gold(state,player,600);player['deck'].remove(card)
            e.log(state,f"{player['name']} 找到战利品地图的宝藏，获得 600 金币")
