"""The per-viewer projection a client renders."""
from ..text import battle_log
from ..content.ascension import monster_value
from copy import deepcopy
from ..content import CARDS, RELICS, POTIONS, PROTOCOL_VERSION, card_view
from ..content.characters import CHARACTERS
from ..combat import battle
from ..combat import damage
from ..combat import play
from . import actions

def view(s,uid):
    if not s.get('battleId') and s.get('phase')=='combat':
        s=deepcopy(s);battle_log.legacy(s)
    from .turn_tasks import choice_state
    receiver_options=actions.options(s,s['players'][str(uid)])
    choice_owners={str(s[key]['owner']) for key in ('pendingChoice','pendingDecision') if s.get(key)}
    s=choice_state(s,uid)
    p=s['players'][str(uid)]
    members=[{k:deepcopy(x[k]) for k in ('id','name','hp','maxHp','gold','block','energy','powers','ready','done','vote')} for x in s['players'].values()]
    # The end-turn control is a three-state thing -- end, undo, or waiting --
    # and the reason rides along so the client never has to infer it.
    end_turn=battle.end_turn_state(s,p)
    from ..combat.orbs import view as orb_view
    from ..combat.osty import companions
    from ..text.power_details import details as power_details
    for member,original in zip(members,s['players'].values()):
        member['companions']=companions(original)
        if details:=power_details(s,original,uid):member['powerDetails']=details
        # Flame Barrier is the only source of a player's thorns; show it as the official status.
        if 'thorns' in member['powers']:member['powers']['flameBarrier']=member['powers'].pop('thorns')
        if original['powers'].get('monologue'):
            records=original.get('monologueInstances')
            if records is None:records=[{'strength':original['powers']['monologue'],'applied':original.get('monologueApplied',0)}]
            member['monologueInstances']=[{'strength':record['strength'],'applied':record['applied']} for record in records]
        if original['powers'].get('surrounded'):member['powers']['facingLeft' if original.get('facing','right')=='left' else 'facingRight']=1
        member.update(character=original.get('character','ironclad'),characterName=CHARACTERS[original.get('character','ironclad')]['name'])
        member.update(stars=original.get('stars',0),orbs=orb_view(original),orbCapacity=original.get('orbCapacity',0),energyCapacity=original.get('energyCapacity',original.get('energy',0)))
        if original.get('osty'):member['osty']={key:original['osty'][key] for key in ('hp','maxHp')}
    enemies=[]
    for e in s['enemies']:
        row={k:deepcopy(e[k]) for k in ('id','name','hp','maxHp','block','powers')};v=e['intent'];row['intent']=deepcopy(v)
        if e.get('hpDisplay'):row['hpDisplay']=e['hpDisplay']
        if e.get('escaped'):row['escaped']=True
        stolen=[card_view(record['card']) for record in e.get('stolenCards',[]) if record['owner']==str(uid)]
        if stolen:row['stolenCards']=stolen
        if e.get('awaitingRevive') or e.get('pendingReattach') or e.get('pendingIllusion'):row['awaitingRevive']=True
        if e['powers'].get('hardenedShell'):row['powers']['hardenedShell']=max(0,e['powers']['hardenedShell']-e.get('shellDamage',0))
        if e['hp']>0 and str(uid) in e.get('sandpits',{}):row['powers']['sandpit']=e['sandpits'][str(uid)]
        if e['key']=='Aeonglass':
            row['powers']['witheringPresence']=e['witheringCounters'][str(uid)]
            if v.get('intensify'):row['intent'].update(strength=monster_value(s,e['key'],'IncreasingIntensityBaseStrength',3)+e.get('additionalStrength',0),status='Wither',count=monster_value(s,e['key'],'WitherAmount',1))
        if e.get('stunned'):row['powers']['stunned']=1;row['intent']={'targets':[],'stunned':True}
        if v.get('damage') and not e.get('stunned'):row['intent']['damageByTarget']={str(i):damage.damage_amount(e,s['players'][str(i)],v['damage']) for i in v['targets']}
        from ..text.intents import display as display_intent
        row['intentDisplay']=display_intent(e,row['intent'],uid)
        if details:=power_details(s,e,uid):row['powerDetails']=details
        enemies.append(row)
    # A pile inspection reveals its contents, never the next draw order.
    rarity_order={key:i for i,key in enumerate(('none','basic','common','uncommon','rare','ancient','event','token','status','curse','quest'))}
    draw_cards=sorted(p['draw'],key=lambda c:(rarity_order.get(CARDS[c['key']]['rarity'],0),c['key'],c['id']))
    result={'protocol':PROTOCOL_VERSION,'mode':s.get('mode','coop'),'rules':s['rules'],'content':s['content'],'revision':s['revision'],'phaseId':s['phaseId'],'phase':s['phase'],'paused':s['paused'],'floor':s['floor'],'turn':s['turn'],
            'endTurn':end_turn,'players':members,'enemies':enemies,'event':actions.EVENTS.get(s['event']), 'log':[battle_log.project(row,uid) for row in s.get('log',[])[-20:] if isinstance(row,dict) and row.get('battleId')], 'battleLog':battle_log.metadata(s), 'self':{'id':p['id'],'hand':[card_view(c) for c in p['hand']],'deck':[card_view(c) for c in p['deck']],'draw':[card_view(c) for c in draw_cards],'discard':[card_view(c) for c in p['discard']],'exhaust':[card_view(c) for c in p['exhaust']],'drawCount':len(p['draw']),'exhaustCount':len(p['exhaust']),'relics':[{'key':k,'name':RELICS[k][0],'description':RELICS[k][1]} for k in p['relics']],'potions':[{**x,'name':POTIONS[x['key']][0],'description':POTIONS[x['key']][1]} for x in p['potions']]},'options':receiver_options}
    # The canonical seed, published so a player can reproduce the run exactly.
    result['seed']=s['seed']
    result['ascension']=s.get('ascension',0)
    result['self']['hand']=[play.combat_card_view(s,p,c) for c in p['hand']]
    for row in result['self']['relics']:
        if row['key'] in p.get('waxRelics',[]):
            row['wax']=True;row['description']='【蜡制】'+row['description']
        if row['key']=='ToyBox':
            row['description']+=f"；已完成 {p.get('toyBoxCombats',0)}/15 场战斗，剩余 {len(p.get('waxRelics',[]))} 件蜡制遗物"
    for key in p.get('meltedRelics',[]):
        result['self']['relics'].append({'key':key,'name':RELICS[key][0],'description':'【已融化】后续遗物效果失效；已发生的永久变化保留','melted':True})
    if 'journey' in s:
        from ..run.map.journey import display, summary
        result['act']=summary(s);result['mapView']=display(s)
    for item in result['self']['relics']:
        if item['key']=='Nunchaku':
            item['counter']=p.get('nunchakuAttacks',0)%10;item['description']+=f"（进度 {item['counter']}/10）"
        if item['key']=='WongosMysteryTicket':
            item['counter']=max(0,5-p.get('wongoCombats',0))
            item['description']+='（已兑现）' if p.get('wongoTicketUsed') else f"（还需 {item['counter']} 场战斗）"
        if s['phase']=='combat' and item['key'] in ('Shuriken','Kunai','OrnamentalFan'):
            item['counter']=p.get('relicCombat',{}).get('attackCounters',{}).get(item['key'],0)%3
            item['description']+=f"（本回合进度 {item['counter']}/3）"
        if s['phase']=='combat' and item['key']=='CentennialPuzzle':
            item['description']+='（本场已触发）' if p.get('relicCombat',{}).get('centennialPuzzleUsed') else '（本场未触发）'
        if item['key']=='Girya':item['counter']=p.get('giryaLifts',0)
        if item['key']=='PollinousCore':item['counter']=p.get('pollinousTurns',0)
        if item['key'] in ('BoneTea','EmberTea','TeaOfDiscourtesy'):
            item['counter']=p.get('teaUses',{}).get(item['key'],5 if item['key']=='EmberTea' else 1)
            item['description']+=f"（剩余 {item['counter']} 次）"
        if item['key']=='SilkenTress':item['description']+='（已使用）' if p.get('silkenTressUsed') else '（尚未使用）'
        if item['key']=='FishingRod':
            item['counter']=p.get('fishingRodCombats',0)%3;item['description']+=f"（进度 {item['counter']}/3）"
        if item['key']=='WingedBoots':
            item['counter']=max(0,3-p.get('wingedBootsUsed',0));item['description']+=f"（剩余 {item['counter']} 次）"
        if item['key']=='SwordOfStone':
            item['counter']=p.get('swordOfStoneElites',0)
            item['description']+=f"（已击败 {item['counter']}/5）"
        if item['key']=='SilverCrucible':
            item['counter']=max(0,3-p.get('crucibleRewards',0))
            item['description']+=f"（剩余 {item['counter']} 次奖励；已进入 {p.get('crucibleTreasures',0)} 个宝箱）"
    from ..content.potions import DATA as potion_data
    from ..run.potions import capacity
    result['self']['potionCapacity']=capacity(p)
    from ..run.events.events import potions_locked
    result['self']['potionsLocked']=bool(potions_locked(s,p))
    for item in result['self']['potions']:item.update(usage=potion_data[item['key']]['usage'],target=potion_data[item['key']]['target'])
    owners={str(row['value']['owner']) for row in s.get('turnChoices',[])}
    owners.update(choice_owners)
    result['choiceStatus']=[{'id':member['id'],'status':'choosing' if str(member['id']) in owners else 'done' if member['done'] else 'ready'} for member in s['players'].values()]
    if s.get('pendingChoice'):
        result['pendingChoice']={k:deepcopy(s['pendingChoice'][k]) for k in ('id','owner','title','minimum','maximum')}
    if s.get('pendingDecision'):
        result['pendingDecision']={k:deepcopy(s['pendingDecision'][k]) for k in ('id','owner','kind','title','minimum','maximum')}
        from .decisions import candidate_options
        result['pendingDecision']['options']=candidate_options(s,p)
    result['self']['pendingCardRewards']=len(p.get('pendingCardRewards',[]))
    result['self']['pendingRelicRewards']=len(p.get('pendingRelicRewards',[]))
    if s.get('eventState'):
        from ..run.events.events import NAMES, view as event_view
        result['event']=NAMES[s['event']];result['eventProgress']=event_view(s,p)
    return result
