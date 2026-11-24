"""Owner-specific, serializable gold rewards; gold changes on claim only."""
from ... import engine as e


def queue(state,player,amount,source):
    if amount<=0:return
    state['serial']+=1
    player.setdefault('pendingGoldRewards',[]).append({'id':'goldReward:'+str(state['serial']),'amount':amount,'source':source})


def claim(state,player,action):
    rewards=player.get('pendingGoldRewards',[])
    reward=next((r for r in rewards if r['id']==action.get('reward')),None)
    e.require(reward is not None,'金币奖励不存在或已处理。')
    e.require(action.get('choice') in ('claim','skip'),'无效的金币奖励操作。')
    rewards.remove(reward)
    if action['choice']=='claim':e.gain_gold(state,player,reward['amount'],stolen_back=reward['source']=='recovered')


def options(player):
    rows=[]
    for reward in player.get('pendingGoldRewards',[]):
        source={'combat':'战斗奖励','recovered':'追回金币','Royalties':'王室贡金'}.get(reward['source'],'金币奖励')
        for choice,label in (('claim',f"领取 {reward['amount']} 金币"),('skip',f"放弃 {reward['amount']} 金币")):
            rows.append({'id':reward['id']+':'+choice,'label':source+'：'+label,'action':{'type':'goldReward','reward':reward['id'],'choice':choice}})
    return rows
