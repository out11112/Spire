"""Pet state shared by future summon cards, relics and potions."""
from .. import engine as e

# These source MonsterModel identities are player companions, never enemy
# encounter candidates. Their gameplay hooks belong to powers/cards/relics.
COMPANION_MODELS={'Osty':{'baseHp':1,'healthBar':True},
                  'Byrdpip':{'baseHp':9999,'healthBar':False},
                  'PaelsLegion':{'baseHp':9999,'healthBar':False}}


def companions(player):
    rows=[]
    for key in ('Byrdpip','PaelsLegion'):
        if key not in player['relics']:continue
        row={'key':key,'name':e.RELICS[key][0]}
        if key=='PaelsLegion':row['cooldown']=max(0,player.get('paelsLegionCooldown',0))
        rows.append(row)
    return rows


def alive(player):return player.get('osty',{}).get('hp',0)>0


def summon(state,player,amount):
    if amount<=0 or player['hp']<=0:return
    if alive(player):
        player['osty']['hp']+=amount;player['osty']['maxHp']+=amount
    else:
        player['osty']={'id':f"osty:{player['id']}",'owner':player['id'],'name':f"{player['name']}的奥斯提",'hp':amount,'maxHp':amount,'block':0,'powers':{}}
    e.log(state,f"{player['name']} 召唤 {amount}：奥斯提 {player['osty']['hp']} HP")
