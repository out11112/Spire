"""Shared treasure selection, conflict rounds and consolation allocation."""
from ... import engine as e


def _lane(state, draw):
    """Generation, fights and consolation share the run treasure stream."""
    from ...rng import streams
    with streams.open(state) as rngs:
        return draw(rngs.run('TreasureRoomRelics'))


def _players(state):
    e.ensure_player_seats(state)
    return sorted(state['players'].values(),key=lambda player:player['seat'])


def enter(state):
    from ...relics.pool import initialize, pull_bag
    from ...relics.hooks import generates_treasure
    from .odds import relic_rarity
    initialize(state)
    for player in _players(state):
        if generates_treasure(player):
            gold=e.player_rng(state,player,'Rewards',lambda rng:rng.next_int_range(42,53))
            if state.get('ascension',0)>=3:gold=int(gold*.75)
            e.gain_gold(state,player,gold)
            from ..map.quests import treasure_reward
            treasure_reward(state,player)
    keys=[pull_bag(state,state['sharedRelicBag'],relic_rarity(state,treasure=True))
          for player in _players(state) if generates_treasure(player)]
    state['treasure']={'relics':keys,'votes':{},'results':[],'resolved':not keys}


def fight(state,players):
    active=list(players);rounds=[]
    while len(active)>1:
        moves={uid:_lane(state,lambda rng:rng.next_int(3)) for uid in active}
        rounds.append(moves);distinct=list(dict.fromkeys(moves.values()))
        if len(distinct)==2:
            first,second=distinct
            losing=first if (first+1)%3==second else second
            active=[uid for uid in active if moves[uid]!=losing]
    return active[0],rounds


def pick(state,player,index):
    record=state.get('treasure')
    e.require(state['phase']=='treasure' and record and not record['resolved'],'当前没有待选择的宝箱。')
    e.require(index is None or type(index) is int and 0<=index<len(record['relics']),'宝箱选项无效。')
    record['votes'][str(player['id'])]=index
    ids=[str(player['id']) for player in _players(state)]
    if not all(uid in record['votes'] for uid in ids):return
    results=[];unclaimed=[]
    for position,key in enumerate(record['relics']):
        voters=[uid for uid in ids if record['votes'][uid]==position]
        if not voters:unclaimed.append((position,key));continue
        winner,rounds=fight(state,voters) if len(voters)>1 else (voters[0],[])
        results.append({'index':position,'key':key,'player':winner,
                        'reason':'fight' if rounds else 'sole','rounds':rounds})
    winners={r['player'] for r in results}
    losers=[uid for uid in ids if uid not in winners and record['votes'][uid] is not None]
    from ...rng.mega_random import snake_case
    # Stable ordering precedes the source's consolation shuffle.
    unclaimed=_lane(state,lambda rng:rng.shuffle(sorted(unclaimed,key=lambda row:snake_case(row[1]).upper())))
    for offset,(position,key) in enumerate(unclaimed):
        winner=losers[offset] if offset<len(losers) else None
        results.append({'index':position,'key':key,'player':winner,
                        'reason':'consolation' if winner else 'skipped','rounds':[]})
    record.update(results=results,resolved=True)
    for result in results:
        if result['player'] is None:continue
        recipient=state['players'][result['player']];state['serial']+=1
        recipient.setdefault('pendingRelicRewards',[]).append(
            {'id':'treasureReward:'+str(state['serial']),'key':result['key']})
        e.log(state,f"宝箱：{recipient['name']} 分得 {e.RELICS.get(result['key'],(result['key'],''))[0]}"+
              ('（猜拳获胜）' if result['reason']=='fight' else '（安慰奖）' if result['reason']=='consolation' else ''))


def options(state,player):
    def opt(id,label,action):return {'id':id,'label':label,'action':action,'choice':None}
    record=state.get('treasure')
    if not record or record['resolved']:
        return [opt('continue','离开宝箱',{'type':'continue'})]
    voted=record['votes'].get(str(player['id']),-1)
    rows=[]
    for index,key in enumerate(record['relics']):
        name,description=e.RELICS.get(key,(key,'效果尚未实现，领取会明确拒绝'))
        count=sum(value==index for value in record['votes'].values())
        rows.append(opt('treasure:'+str(index),f"{'已选 · ' if voted==index else ''}{name}：{description}（{count} 人选择）",
                          {'type':'treasurePick','index':index}))
    rows.append(opt('treasure:skip','已选择放弃（可改选）' if voted is None else '放弃宝箱遗物',{'type':'treasurePick','index':None}))
    return rows
