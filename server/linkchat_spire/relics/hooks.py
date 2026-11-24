"""Relic lifecycle hooks; acquisition pools are audited separately."""
from .. import engine as e
from ..content.data import load as load_data

DATA=load_data('relic_data.json')


def available(state,player,*,shop=False):
    # Compatibility inventory query. Actual acquisition uses relic_pool's full
    # persistent source bags and eligibility rules.
    rarities=('common','uncommon','rare','shop') if shop else ('common','uncommon','rare')
    return [key for key in e.RELICS if key not in player['relics'] and DATA[key]['rarity'] in rarities
            and DATA[key]['pool'] in ('shared',player.get('character','ironclad'))
            and (key!='WhiteBeastStatue' or state['floor']<(38 if len(state['players'])>1 else 41))]


def inventory_changed(state,player):
    if state['phase']!='combat' or 'BeltBuckle' not in player['relics'] or player['hp']<=0:return
    active=not player['potions'];previous=player.get('beltBuckleApplied',False)
    if active!=previous:
        player['beltBuckleApplied']=active;e.power(player,'dexterity',2 if active else -2)


def obtained(state,player,key):
    from .shop import obtained as shop_obtained
    shop_obtained(state,player,key)
    from ..run.events.ancient_relics import obtained as ancient_obtained
    ancient_obtained(state,player,key)
    from .map import obtained as map_obtained
    map_obtained(state,player,key)
    if key=='ToyBox':
        from ..run.rewards.custom import queue_relic
        for _ in range(5):queue_relic(state,player)['wax']=True
    if key=='PumpkinCandle':player['pumpkinCombats']=player.get('pumpkinCombats',0)+5
    if key=='SignetRing':e.gain_gold(state,player,888)
    elif key=='PaelsHorn':
        for _ in range(2):e.obtain_card(state,player,e.new_card(state,'Relax'))
    elif key=='SereTalon':
        e.lose_max_hp(state,player,9)
        for _ in range(3):e.obtain_card(state,player,e.new_card(state,'Wish'))
    elif key=='SandCastle':
        for card in e.stable_card_shuffle(state,'Niche',[c for c in player['deck'] if e.upgradable(c)])[:6]:e.upgrade(card)
    elif key=='PreservedFog':
        from ..combat.effects import select_now
        select_now(state,player,{'op':'select','source':'deck','destination':'removeDeck','cards':[c for c in player['deck'] if e.removable(c)],'minimum':3,'maximum':3,'title':'腌制活雾：移除三张牌'})
        e.obtain_card(state,player,e.new_card(state,'Folly'))
    if key=='FakeLeesWaffle':e.heal(player,player['maxHp']//10)
    elif key=='FakeMango':player['maxHp']+=3;e.heal(player,3)
    elif key in ('FakeSneckoEye','SneckoEye') and state['phase']=='combat':e.debuff(state,player,player,'confused',1)
    if key=='LoomingFruit':player['maxHp']+=31;e.heal(player,31)
    elif key=='JewelryBox':e.obtain_card(state,player,e.new_card(state,'Apotheosis'))
    elif key=='AlchemicalCoffer':
        from ..run.potions import generate, procure
        player['potionCapacity']=player.get('potionCapacity',3)+4
        for item in generate(state,player,4,source='combat'):procure(state,player,item)
    elif key in ('BeautifulBracelet','NutritiousSoup'):
        from ..combat.enchantments import can_enchant, enchant
        enchantment='Swift' if key=='BeautifulBracelet' else 'TezcatarasEmber'
        cards=[card for card in player['deck'] if can_enchant(card,enchantment,in_deck=True)]
        if key=='BeautifulBracelet':cards=e.niche_shuffled(state,cards)[:4]
        else:cards=[card for card in cards if e.definition(card)['rarity']=='basic' and e.definition(card)['values'].get('strike')]
        for card in cards:enchant(card,enchantment,in_deck=True,amount=2 if key=='BeautifulBracelet' else 1)
    elif key in ('BiiigHug','YummyCookie'):
        from ..combat.effects import select_now
        remove=key=='BiiigHug'
        cards=[c for c in player['deck'] if (e.removable(c) if remove else e.upgradable(c))]
        select_now(state,player,{'op':'select','source':'deck','destination':'removeDeck' if remove else 'upgrade',
            'cards':cards,'minimum':4,'maximum':4,'title':key+'：选择四张牌'})
    if key=='DollysMirror':
        from ..core.decisions import select
        cards=[card for card in player['deck'] if e.definition(card)['kind']!='quest']
        if cards:
            rows=[{'id':card['id'],'label':e.card_view(card)['name']+'：'+e.card_view(card)['description']} for card in cards]
            selected=select(state,player,'copyDeck','多莉的魔镜：复制一张非任务牌',rows)
            if selected:e.obtain_card(state,player,e.copy_card(state,e.find_card(player['deck'],selected[0]['id'])))
    elif key in ('Whetstone','WarPaint'):
        kind='attack' if key=='Whetstone' else 'skill'
        cards=[c for c in player['deck'] if e.CARDS[c['key']]['kind']==kind and e.upgradable(c)]
        for card in e.stable_card_shuffle(state,'Niche',cards)[:2]:e.upgrade(card)
    elif key in ('EmptyCage','Astrolabe'):
        from ..combat.effects import select_now
        count=2 if key=='EmptyCage' else 3
        select_now(state,player,{'op':'select','source':'deck','cards':[c for c in player['deck'] if e.removable(c)],
            'destination':'removeDeck' if key=='EmptyCage' else 'randomTransform','upgradeTransform':key=='Astrolabe',
            'minimum':count,'maximum':count,'stream':'niche','title':e.RELICS[key][0]+'：选择卡牌'})
    elif key=='PandorasBox':
        from ..run.events.transforms import replacement, replace_in_pile
        basics={k for c in e.CHARACTERS.values() for k in c['deck'] if k.startswith(('Strike','Defend'))}
        cards=[c for c in player['deck'] if c['key'] in basics and e.removable(c)]
        replacements=[replacement(state,player,c,in_combat=False,source='niche') for c in cards]
        for card,new in zip(cards,replacements):replace_in_pile(state,player,player['deck'],card,new)
    elif key=='CallingBell':
        from ..run.rewards.custom import queue_relic
        e.obtain_card(state,player,e.new_card(state,'CurseOfTheBell'))
        for rarity in ('common','uncommon','rare'):queue_relic(state,player,rarity)
    elif key=='Orrery':
        from ..run.rewards.custom import offer_cards
        for _ in range(5):offer_cards(state,player)
    elif key=='NeowsBones':
        from ..run.events.neow import bones
        bones(state,player)
    elif key=='SilkenTress':player['gold']=0
    elif key=='SmallCapsule':
        from ..run.rewards.custom import offer_relic
        offer_relic(state,player)
    elif key=='LargeCapsule':
        from .pool import pull
        for _ in range(2):e.relic(state,player,pull(state,player))
        for prefix in ('Strike','Defend'):
            basic=next(k for k in e.CHARACTERS[player['character']]['deck'] if k.startswith(prefix))
            e.obtain_card(state,player,e.new_card(state,basic))
    elif key=='Kaleidoscope':
        from ..run.rewards.custom import offer_instances
        for _ in range(2):
            pools=e.niche_shuffled(state,sorted((key for key in e.CHARACTERS if key!=player['character']),key=lambda key:key.upper()+'_CARD_POOL'))[:3]
            cards=[]
            for pool in pools:
                definition=e.card_choices(state,player,[d for d in e.CARDS.values() if d['pool']==pool],source='other',count=1,act_index=state.get('actIndex',0))[0]
                cards.append(e.new_card(state,definition['key'],definition['upgraded']))
            offer_instances(state,player,cards)
    elif key=='MassiveScroll':
        from ..combat.effects import select_now
        pool=[d for d in e.CARDS.values() if d['pool'] in (player['character'],'colorless') and d['values'].get('multiplayerOnly')]
        cards=e.card_choices(state,player,pool,source='other',count=3,act_index=state.get('actIndex',0))
        select_now(state,player,{'op':'select','source':'generated','destination':'deck',
            'cards':[e.new_card(state,c['key'],c['upgraded']) for c in cards],'minimum':0,'maximum':1,'title':'巨型卷轴：选择一张多人牌或跳过'})
    elif key=='ScrollBoxes':
        from ..run.events.neow import scroll_bundles
        scroll_bundles(state,player)
    elif key=='PhialHolster':
        from ..run.potions import generate, procure
        player['potionCapacity']=player.get('potionCapacity',3)+1
        for item in generate(state,player,2,source='combat'):procure(state,player,item)
    elif key=='NeowsTalisman':
        for prefix in ('Strike','Defend'):
            card=next((c for c in reversed(player['deck']) if e.CARDS[c['key']]['rarity']=='basic' and c['key'].startswith(prefix)),None)
            if card and e.upgradable(card):e.upgrade(card)
    elif key=='Pomander':
        from ..combat.effects import select_now
        select_now(state,player,{'op':'select','source':'deck','destination':'upgrade','cards':[c for c in player['deck'] if e.upgradable(c)],
                                 'minimum':1,'maximum':1,'title':'香球：选择升级一张牌'})
    elif key in ('ArcaneScroll','HeftyTablet','LeadPaperweight'):
        from ..combat.effects import select_now
        pool=([d for d in e.CARDS.values() if d['pool']=='colorless'] if key=='LeadPaperweight'
              else [d for d in e.reward_pool(player) if d['rarity']=='rare'])
        cards=e.card_choices(state,player,pool,source='other' if key=='LeadPaperweight' else 'event',
                             count={'ArcaneScroll':1,'HeftyTablet':3,'LeadPaperweight':2}[key],uniform=key!='LeadPaperweight',act_index=state.get('actIndex',0))
        cards=[e.new_card(state,c['key'],c['upgraded']) for c in cards]
        if key=='ArcaneScroll':
            for card in cards:e.obtain_card(state,player,card)
        else:select_now(state,player,{'op':'select','source':'generated','destination':'deck','cards':cards,
                                     'minimum':0,'maximum':1,'title':e.RELICS[key][0]+'：选择一张牌或跳过'})
        if key=='HeftyTablet':e.obtain_card(state,player,e.new_card(state,'Injury'))
    elif key in ('PreciseScissors','PrecariousShears'):
        from ..combat.effects import select_now
        count=1 if key=='PreciseScissors' else 2
        select_now(state,player,{'op':'select','source':'deck','destination':'removeDeck','cards':[c for c in player['deck'] if e.removable(c)],
                                 'minimum':count,'maximum':count,'title':e.RELICS[key][0]+'：选择移除卡牌'})
        if key=='PrecariousShears':e.hit(state,player,player,16,True)
    elif key=='NeowsTorment':e.obtain_card(state,player,e.new_card(state,'NeowsFury'))
    elif key=='DowsingRod':e.obtain_card(state,player,e.new_card(state,'Dowsing'))
    elif key=='NeowsSacrifice':
        from ..run.potions import create, procure
        procure(state,player,create(state,'Ambergris'))
        e.obtain_card(state,player,e.new_card(state,'Guilty'))
    elif key=='GoldenPearl':e.gain_gold(state,player,150)
    elif key=='CursedPearl':e.obtain_card(state,player,e.new_card(state,'Greed'));e.gain_gold(state,player,333)
    elif key=='NewLeaf':
        from ..combat.effects import select_now
        select_now(state,player,{'op':'select','source':'deck','destination':'randomTransform',
            'cards':[c for c in player['deck'] if e.removable(c)],'minimum':1,'maximum':1,'title':'新叶：选择变换一张牌','stream':'niche'})
    elif key=='LeafyPoultice':
        from ..run.events.transforms import replacement, replace_in_pile
        e.lose_max_hp(state,player,12)
        for prefix in ('Strike','Defend'):
            card=next((c for c in player['deck'] if e.CARDS[c['key']]['rarity']=='basic' and c['key'].startswith(prefix)),None)
            if card:replace_in_pile(state,player,player['deck'],card,replacement(state,player,card,in_combat=False))
    elif key=='PotionBelt':player['potionCapacity']=player.get('potionCapacity',3)+2
    elif key=='BeltBuckle':inventory_changed(state,player)
    elif key=='Cauldron':
        from ..run.potions import reward
        reward(state,player,5)
    elif key=='LostCoffer':
        from ..run.rewards.custom import offer_cards
        from ..run.potions import reward
        offer_cards(state,player);reward(state,player)
    elif key=='OldCoin':e.gain_gold(state,player,300)
    elif key in ('Pear','Mango','LeesWaffle','BigMushroom','NutritiousOyster'):
        amount={'Pear':10,'Mango':14,'LeesWaffle':7,'BigMushroom':20,'NutritiousOyster':11}[key]
        player['maxHp']+=amount;e.heal(player,player['maxHp'] if key=='LeesWaffle' else amount)
    elif key=='FragrantMushroom':
        e.lose_hp(state,player,15)
        for card in e.stable_card_shuffle(state,'Niche',[c for c in player['deck'] if e.upgradable(c)])[:2]:e.upgrade(card)


def room_entered(state,player,kind):
    if kind=='rest' and 'FakeVenerableTeaSet' in player['relics']:player['fakeTeaSetArmed']=True
    if kind=='rest' and 'VenerableTeaSet' in player['relics']:player['teaSetArmed']=True
    player.pop('lavaLampDamaged',None)
    if kind=='rest':player['restUsed']=[]
    if kind=='rest' and 'EternalFeather' in player['relics']:e.heal(player,len(player['deck'])//5*3)
    if kind=='treasure' and 'SilverCrucible' in player['relics']:player['crucibleTreasures']=player.get('crucibleTreasures',0)+1
    if 'MealTicket' in player['relics'] and kind=='shop' and player['hp']>0:e.heal(player,15)
    if 'MawBank' in player['relics'] and not player.get('mawBankSpent'):e.gain_gold(state,player,12)


def modify_acquired_card(player,card,*,reward_preview=False):
    kind=e.definition(card)['kind']
    egg={'attack':'MoltenEgg','skill':'ToxicEgg','power':'FrozenEgg'}.get(kind)
    if egg in player.get('relics',[]) and not card.get('upgraded') and e.upgradable(card):e.upgrade(card)
    if not reward_preview and 'FresnelLens' in player.get('relics',[]):
        from ..combat.enchantments import can_enchant, enchant
        if can_enchant(card,'Nimble',in_deck=True):enchant(card,'Nimble',in_deck=True,amount=2)


def card_added(state,player,card,*,cloned_by=None):
    if 'BookOfFiveRings' in player['relics'] and player['hp']>0:
        player['fiveRingsCards']=player.get('fiveRingsCards',0)+1
        if player['fiveRingsCards']%5==0:e.heal(player,20)
    if 'LuckyFysh' in player['relics']:e.gain_gold(state,player,15)
    if 'DarkstonePeriapt' in player['relics'] and e.CARDS[card['key']]['kind']=='curse':
        player['maxHp']+=6;e.heal(player,6)
    if 'BingBong' in player['relics'] and cloned_by is None:
        e.obtain_card(state,player,e.copy_card(state,card),cloned_by='BingBong')


def hand_draw_bonus(player):
    bonus=2 if 'RingOfTheDrake' in player['relics'] and player.get('turnNumber',0)<=3 else 0
    if 'SneckoEye' in player['relics']:bonus+=2
    if 'Fiddle' in player['relics']:bonus+=2
    if 'PaelsBlood' in player['relics']:bonus+=1
    if 'Pocketwatch' in player['relics'] and player.get('turnNumber',0)>1 and player.get('pocketwatchLast',0)<=3:bonus+=3
    if 'Pendulum' in player['relics']:
        player['pendulumTurns']=(player.get('pendulumTurns',0)+1)%3
        if player['pendulumTurns']==0:bonus+=1
    if 'PollinousCore' in player['relics']:
        player['pollinousTurns']=(player.get('pollinousTurns',0)+1)%4
        if player['pollinousTurns']==0:bonus+=2
    return bonus


def card_reward_options(player,cards,state=None,*,is_card_reward=True):
    if 'Glitter' in player['relics']:
        from ..combat.enchantments import can_glam, glam
        for card in cards:
            if can_glam(card):glam(card)
    # Silver Crucible and Silken Tress only spend a charge on a real card
    # reward; the reference gates them on the reward flag, which generated
    # option sets such as Sea Glass do not carry.
    if is_card_reward and 'SilverCrucible' in player['relics'] and player.get('crucibleRewards',0)<3:
        for card in cards:
            if e.upgradable(card):e.upgrade(card)
        player['crucibleRewards']=player.get('crucibleRewards',0)+1
    if is_card_reward and 'SilkenTress' in player['relics'] and not player.get('silkenTressUsed'):
        from ..combat.enchantments import can_glam, glam
        for card in cards:
            if can_glam(card):glam(card)
        player['silkenTressUsed']=True
    if 'FresnelLens' in player['relics']:
        from ..combat.enchantments import can_enchant, enchant
        for card in cards:
            if can_enchant(card,'Nimble',in_deck=True):enchant(card,'Nimble',in_deck=True,amount=2)
    if state is not None:
        from .shop import reward_options
        reward_options(state,player,cards)


def generates_treasure(player):
    return 'SilverCrucible' not in player['relics'] or player.get('crucibleTreasures',0)>1


def combat_start(state,player):
    player.pop('unsettlingLampCard',None);player.pop('unsettlingLampUsed',None)
    player['manualFinished']=0;player.pop('paelsEyeUsed',None);player.pop('paelsEyeExtra',None)
    player['beatingRemnantLoss']=0;player['brilliantScarfPlays']=0;player['paelsLegionCooldown']=0;player.pop('paelsLegionCard',None)
    player['rainbowKinds']=[];player.pop('rainbowUsed',None)
    player['kusarigamaAttacks']=0;player['jossPaperEthereal']=0
    player.pop('vambraceCard',None);player.pop('vambraceUsed',None);player.pop('penNibCard',None)
    if 'StoneCracker' in player['relics']:
        for card in e.stable_card_shuffle(state,'CombatCardSelection',[c for c in e.top_first(player['draw']) if e.upgradable(c)])[:2]:e.upgrade(card)
    player.pop('throwingAxeUsed',None);player.pop('paelsTearsEnergy',None)
    player.pop('musicBoxUsed',None);player.pop('musicBoxCard',None)
    if 'DelicateFrond' in player['relics']:
        from ..run.potions import generate, procure, capacity
        while len(player['potions'])<capacity(player):
            if not procure(state,player,generate(state,player,source='combat')[0]):break
    player['metronomeOrbs']=0;player.pop('emotionChipLast',None);player.pop('emotionChipDamaged',None)
    if any(key in player['relics'] for key in ('FakeSneckoEye','SneckoEye')):e.debuff(state,player,player,'confused',1)
    player['velvetChokerPlayed']=0
    if 'PhilosophersStone' in player['relics']:
        for enemy in state['enemies']:
            if enemy['hp']>0:e.power(enemy,'strength',1)
    player.pop('regaliteUsed',None)
    player.pop('permafrostUsed',None);player.pop('miniRegentUsed',None)
    if player['hp']>0 and state.get('encounterKind')=='boss' and 'Pantograph' in player['relics']:e.heal(player,25)
    player['letterOpenerSkills']=0
    player['pocketwatchPlayed']=0;player['pocketwatchLast']=0
    if 'DataDisk' in player['relics']:e.power(player,'focus',1)
    if 'Gorget' in player['relics']:e.power(player,'plating',4)
    if 'PhylacteryUnbound' in player['relics']:
        from ..combat.osty import summon
        summon(state,player,5)
    player.pop('lavaLampDamaged',None)
    from .shop import entered_card
    from ..combat.classes.defect import combat_cards
    for card in combat_cards(state,player):entered_card(player,card)
    if state['encounterKind']=='elite' and 'SlingOfCourage' in player['relics']:e.power(player,'strength',2)
    if 'BronzeScales' in player['relics']:e.power(player,'permanentThorns',3)
    player.pop('artOfWarAttack',None);player.pop('artOfWarLastAttack',None)
    player['beltBuckleApplied']=False;inventory_changed(state,player)
    hp_changed(player)
    if 'SwordOfJade' in player['relics']:e.power(player,'strength',3)
    if 'Girya' in player['relics']:e.power(player,'strength',player.get('giryaLifts',0))
    if consume_tea(player,'EmberTea',5):e.power(player,'strength',2)
    if consume_tea(player,'TeaOfDiscourtesy',1):
        for _ in range(2):
            card=e.new_card(state,'Dazed');e.add_generated(state,player,card,'draw')
            player['draw'].remove(card);e.insert_at_random(state,player['draw'],card,draw_pile=True)


def consume_tea(player,key,initial):
    if key not in player['relics']:return False
    uses=player.setdefault('teaUses',{});left=uses.get(key,initial)
    if left<=0:return False
    uses[key]=left-1
    return True


def combat_victory_early(state,player):
    if player['hp']>0 and 'MeatOnTheBone' in player['relics'] and player['hp']<=player['maxHp']//2:
        e.heal(player,12)


def combat_victory(state,player):
    if player['hp']>0:
        if 'BurningBlood' in player['relics']:e.heal(player,6)
        if 'BlackBlood' in player['relics']:e.heal(player,12)
    if state.get('encounterKind')=='elite' and 'WarHammer' in player['relics']:
        for card in e.stable_card_shuffle(state,'Niche',[c for c in player['deck'] if e.upgradable(c)])[:4]:e.upgrade(card)
    if state['encounterKind']=='elite' and 'SwordOfStone' in player['relics']:
        player['swordOfStoneElites']=player.get('swordOfStoneElites',0)+1
        if player['swordOfStoneElites']>=5:
            position=player['relics'].index('SwordOfStone');player['relics'].pop(position)
            e.relic(state,player,'SwordOfJade')
            player['relics'].remove('SwordOfJade');player['relics'].insert(position,'SwordOfJade')
            player.pop('swordOfStoneElites',None)


def combat_rewards(state,player):
    if state.get('encounterKind')=='elite' and 'WhiteStar' in player['relics']:
        from ..run.rewards.custom import offer_cards
        offer_cards(state,player,source='boss')
    if 'AmethystAubergine' in player['relics'] and not (state.get('encounterKind')=='boss' and state.get('actIndex',0)>=2):
        from ..run.rewards.gold import queue
        queue(state,player,15,'AmethystAubergine')
    if 'WongosMysteryTicket' in player['relics'] and player.get('wongoCombats',0)>=5 and not player.get('wongoTicketUsed'):
        from ..run.rewards.custom import queue_relic
        for _ in range(3):queue_relic(state,player)
        player['wongoTicketUsed']=True
    if state.get('encounterKind')=='battle' and 'PrayerWheel' in player['relics']:
        from ..run.rewards.custom import offer_cards
        offer_cards(state,player,source='battle')
    if state.get('encounterKind')=='elite' and 'BlackStar' in player['relics']:
        from ..run.rewards.custom import queue_relic
        queue_relic(state,player)
    if ('LavaRock' in player['relics'] and state.get('encounterKind')=='boss'
            and state.get('actIndex',0)==0 and not player.get('lavaRockTriggered')):
        from ..run.rewards.custom import queue_relic
        for _ in range(2):queue_relic(state,player)
        player['lavaRockTriggered']=True


def combat_end(state,player):
    from ..run.events.ancient_relics import combat_end as ancient_combat_end
    ancient_combat_end(state,player)
    if 'ToyBox' in player['relics'] and player.get('toyBoxCombats',0)<15:
        player['toyBoxCombats']=player.get('toyBoxCombats',0)+1
        player['waxRelics']=[key for key in player.get('waxRelics',[]) if key in player['relics']]
        if player['toyBoxCombats']%3==0 and player.get('waxRelics'):
            key=player['waxRelics'].pop(0)
            if key in player['relics']:player['relics'].remove(key)
            player.setdefault('meltedRelics',[]).append(key)
    if 'PumpkinCandle' in player['relics']:player['pumpkinCombats']=max(0,player.get('pumpkinCombats',0)-1)
    if 'WongosMysteryTicket' in player['relics']:player['wongoCombats']=player.get('wongoCombats',0)+1
    if 'ChosenCheese' in player['relics']:player['maxHp']+=1;e.heal(player,1)
    if 'FishingRod' in player['relics'] and state.get('encounterKind')=='battle':
        player['fishingRodCombats']=player.get('fishingRodCombats',0)+1
        if player['fishingRodCombats']%3==0:
            cards=[c for c in player['deck'] if e.upgradable(c)]
            if cards:e.upgrade(e.niche_choose(state,cards))


def after_card(state,player,card):
    for owner in state['players'].values():
        if owner.get('unsettlingLampCard')==card['id']:owner['unsettlingLampUsed']=True
    if not card.get('relicAutoPlay'):player['manualFinished']=player.get('manualFinished',0)+1
    for key in tuple(player['relics']):
        after_card_relic(state,player,card,key)


def after_card_relic(state,player,card,key):
    # Select one listener while keeping the full inventory visible to nested hooks.
    relics=(key,)
    if 'BrilliantScarf' in relics and not card.get('relicAutoPlay'):player['brilliantScarfPlays']=player.get('brilliantScarfPlays',0)+1
    if 'PaelsLegion' in relics and player.get('paelsLegionCard')==card['id']:player['paelsLegionCooldown']=2;player.pop('paelsLegionCard',None)
    if 'IvoryTile' in relics and card.get('resourceEnergyValue',0)>=3:player['energy']+=1
    if 'RazorTooth' in relics and e.definition(card)['kind'] in ('attack','skill') and e.upgradable(card):e.upgrade(card)
    if state['phase']=='combat' and 'RainbowRing' in relics and not player.get('rainbowUsed'):
        kind=e.definition(card)['kind'];kinds=player.setdefault('rainbowKinds',[])
        if kind not in kinds:kinds.append(kind)
        if all(k in kinds for k in ('attack','skill','power')):player['rainbowUsed']=True;e.power(player,'strength',1);e.power(player,'dexterity',1)
    if 'PenNib' in relics and player.get('penNibCard')==card['id']:player.pop('penNibCard',None)
    if 'Vambrace' in relics and player.get('vambraceCard')==card['id']:player['vambraceUsed']=True
    if state['phase']=='combat' and e.definition(card)['kind']=='attack' and 'Kusarigama' in relics:
        player['kusarigamaAttacks']=player.get('kusarigamaAttacks',0)+1
        if player['kusarigamaAttacks']%3==0:
            enemies=[enemy for enemy in state['enemies'] if enemy['hp']>0]
            if enemies:e.hit(state,player,e.random_enemy(state,enemies),6,True)
    if 'MusicBox' in relics and player.get('musicBoxCard')==card['id']:
        player['musicBoxUsed']=True;player.pop('musicBoxCard',None)
        duplicate=e.copy_card(state,card)
        if 'ethereal' not in duplicate.setdefault('addedKeywords',[]):duplicate['addedKeywords'].append('ethereal')
        e.add_generated(state,player,duplicate)
    if state['phase']=='combat' and e.definition(card)['kind']=='power':
        if 'GamePiece' in relics:e.draw(state,player,1)
        if 'MummifiedHand' in relics:
            from ..combat.costs import free
            cards=list(player['hand'])
            base=[c for c in cards if e.CARDS[c['key']]['cost']+(e.CARDS[c['key']]['upgrade'].get('cost',0) if c.get('upgraded') else 0)+c.get('baseCostAdjustment',0)>0 or e.definition(c)['values'].get('starCost',0)>0]
            payable=lambda c:e.energy_cost(state,player,c)>0 or e.star_cost(player,c)>0
            eligible=[c for c in base if payable(c)] or [c for c in cards if payable(c)] or base or cards
            if eligible:free(e.combat_card_selection(state,eligible))
    if 'HelicalDart' in relics and e.definition(card)['values'].get('shiv'):
        e.power(player,'dexterity',1);e.power(player,'helicalDart',1)
    if 'IronClub' in relics:
        player['ironClubCards']=player.get('ironClubCards',0)+1
        if state['phase']=='combat' and player['ironClubCards']%4==0:e.draw(state,player,1)
    if 'VelvetChoker' in relics:player['velvetChokerPlayed']=player.get('velvetChokerPlayed',0)+1
    if e.definition(card)['kind']=='skill' and 'TuningFork' in relics:
        player['tuningForkSkills']=(player.get('tuningForkSkills',0)+1)%10
        if player['tuningForkSkills']==0:e.gain_block(state,player,7,True)
    if state['phase']=='combat' and e.definition(card)['kind']=='power' and 'Permafrost' in relics and not player.get('permafrostUsed'):
        player['permafrostUsed']=True;e.gain_block(state,player,7,True)
    if state['phase']=='combat' and 'LetterOpener' in relics and e.definition(card)['kind']=='skill':
        player['letterOpenerSkills']=player.get('letterOpenerSkills',0)+1
        if player['letterOpenerSkills']%3==0:
            for enemy in list(state['enemies']):
                if enemy['hp']>0:e.hit(state,player,enemy,5,True)
    if state['phase']=='combat' and 'Pocketwatch' in relics:player['pocketwatchPlayed']=player.get('pocketwatchPlayed',0)+1
    if e.definition(card)['kind']=='attack' and 'DaughterOfTheWind' in relics:e.gain_block(state,player,1,True)
    if e.definition(card)['kind']=='attack' and 'Nunchaku' in relics:
        player['nunchakuAttacks']=player.get('nunchakuAttacks',0)+1
        if state['phase']=='combat' and player['nunchakuAttacks']%10==0:player['energy']+=1
    if state['phase']=='combat' and e.definition(card)['kind']=='attack':
        counters=player.setdefault('relicCombat',{}).setdefault('attackCounters',{})
        for key in ('Shuriken','Kunai','OrnamentalFan'):
            if key not in relics:continue
            counters[key]=counters.get(key,0)+1
            if counters[key]%3==0:
                if key=='OrnamentalFan':e.gain_block(state,player,4,True)
                else:e.power(player,'strength' if key=='Shuriken' else 'dexterity',1)
    if state['phase']=='combat' and 'ArtOfWar' in relics and e.definition(card)['kind']=='attack':player['artOfWarAttack']=True
    if state['phase']=='combat' and 'LostWisp' in relics and e.definition(card)['kind']=='power':
        for enemy in list(state['enemies']):
            if enemy['hp']>0:e.hit(state,player,enemy,8,True)


def hp_changed(player):
    context=player.get('relicCombat')
    if context is None or 'RedSkull' not in player.get('relics',[]):return
    active=player['hp']*2<=player['maxHp']
    if active!=context.get('skullApplied',False):
        context['skullApplied']=active
        e.power(player,'strength',3 if active else -3)


def potion_used(state,player):
    inventory_changed(state,player)
    if state['phase']=='combat' and player['hp']>0 and 'ReptileTrinket' in player['relics']:
        e.power(player,'strength',3);e.power(player,'reptileTrinket',3)


def rest_heal(state,player):
    if 'DreamCatcher' in player['relics']:
        from ..run.rewards.custom import offer_cards
        offer_cards(state,player,source='battle')
    if 'StoneHumidifier' in player['relics']:player['maxHp']+=5;e.heal(player,5)
    if 'TinyMailbox' in player['relics']:
        from ..run.potions import reward
        reward(state,player,2)


def before_flush(state,player):
    if 'PaelsTears' in player['relics']:player['paelsTearsEnergy']=player['energy']>0
    if 'RippleBasin' in player['relics'] and not player.get('attacksFinished',0):e.gain_block(state,player,4,True)
    if 'CloakClasp' in player['relics']:e.gain_block(state,player,len(player['hand']),True)
    if 'StoneCalendar' in player['relics'] and player.get('turnNumber')==7:
        for enemy in list(state['enemies']):
            if enemy['hp']>0:e.hit(state,player,enemy,52,True)
    if 'ScreamingFlagon' in player['relics'] and not player['hand']:
        for enemy in state['enemies']:
            if enemy['hp']>0:e.hit(state,player,enemy,20,True)


def turn_end(state,player):
    player['kusarigamaAttacks']=0
    if 'JossPaper' in player['relics']:
        total=player.get('jossPaperCards',0)+player.pop('jossPaperEthereal',0)
        player['jossPaperCards']=total%5
        if total>=5:e.draw(state,player,total//5)
    if player['hp']>0 and 'LunarPastry' in player['relics']:
        from ..combat.classes.regent import gain_stars
        gain_stars(state,player,1)
    if player['hp']>0 and 'ParryingShield' in player['relics'] and player['block']>=10:
        targets=[enemy for enemy in state['enemies'] if enemy['hp']>0]
        if targets:e.hit(state,player,e.random_enemy(state,targets),6,True)
    if 'ArtOfWar' in player['relics']:player['artOfWarLastAttack']=player.pop('artOfWarAttack',False)


def before_side_turn_start(state,participants):
    for player in participants:
        player['manualFinished']=0
        player['beatingRemnantLoss']=0;player['brilliantScarfPlays']=0
        player['rainbowKinds']=[];player.pop('rainbowUsed',None)
        player.pop('musicBoxUsed',None);player.pop('musicBoxCard',None)
        player['emotionChipLast']=player.pop('emotionChipDamaged',False)
        if player['hp']>0 and player.get('turnNumber',0)==0 and 'PowerCell' in player['relics']:
            cards=[c for c in e.top_first(player['draw']) if not e.definition(c)['values'].get('xCost') and e.definition(c)['cost']==0]
            for card in e.stable_card_shuffle(state,'CombatCardSelection',cards)[:2]:
                player['draw'].remove(card);e.add_to_hand(state,player,card)
        player['velvetChokerPlayed']=0
        player.pop('regaliteUsed',None)
        player.pop('miniRegentUsed',None)
        if player['hp']>0 and player.get('turnNumber',0)==0 and 'TwistedFunnel' in player['relics']:
            for enemy in state['enemies']:
                if enemy['hp']>0:e.debuff(state,player,enemy,'poison',4)
        player['pocketwatchLast']=player.get('pocketwatchPlayed',0);player['pocketwatchPlayed']=0
        if player['hp']>0 and player.get('turnNumber',0)==0 and 'RedMask' in player['relics']:
            for enemy in state['enemies']:
                if enemy['hp']>0:e.debuff(state,player,enemy,'weak',1)
        player.setdefault('relicCombat',{}).pop('attackCounters',None)
        if player['hp']>0 and player.get('turnNumber',0)==0 and 'BagOfMarbles' in player['relics']:
            for enemy in state['enemies']:
                if enemy['hp']>0:e.debuff(state,player,enemy,'vulnerable',1)


def after_side_turn_start(state,participants):
    for player in participants:
        if player['hp']>0 and player.get('turnNumber',state['turn'])==1 and state['encounterKind']=='elite' and 'BoomingConch' in player['relics']:player['energy']+=1
        if player['hp']>0 and player.get('turnNumber',state['turn'])==1 and 'VeryHotCocoa' in player['relics']:player['energy']+=4
        if player['hp']>0 and 'Brimstone' in player['relics']:
            e.power(player,'strength',2)
            for enemy in state['enemies']:
                if enemy['hp']>0:e.power(enemy,'strength',1)
        if 'PaelsLegion' in player['relics']:player['paelsLegionCooldown']=player.get('paelsLegionCooldown',0)-1
        if player['hp']>0 and 'PaelsTears' in player['relics'] and player.get('paelsTearsEnergy'):player['energy']+=2
        if player['hp']>0 and 'SealOfGold' in player['relics'] and player['gold']>=3:player['energy']+=1;player['gold']-=3
        if player['hp']>0 and 'Crossbow' in player['relics']:
            from ..combat.effects import generated_cards
            from ..combat.costs import free
            for card in generated_cards(state,player['character'],1,kind='attack'):
                free(card);e.add_generated(state,player,card)
        if player['hp']>0 and 'FakeHappyFlower' in player['relics']:
            player['fakeFlowerTurns']=(player.get('fakeFlowerTurns',0)+1)%5
            if player['fakeFlowerTurns']==0:player['energy']+=1
        if player['hp']>0 and 'Sai' in player['relics']:e.gain_block(state,player,7,True)
        if player['hp']>0 and player.get('turnNumber')==3 and 'Chandelier' in player['relics']:player['energy']+=3
        if player['hp']>0 and player.get('turnNumber')==2 and 'Candelabra' in player['relics']:player['energy']+=2
        if player.get('turnNumber',0)>1:player['letterOpenerSkills']=0
        if player['hp']>0 and 'PhylacteryUnbound' in player['relics']:
            from ..combat.osty import summon
            summon(state,player,2)
        if player['hp']>0 and player.get('turnNumber')==1:
            if 'DiamondDiadem' in player['relics']:e.gain_block(state,player,20,True);e.power(player,'blur',1)
            if 'BigHat' in player['relics']:
                from ..combat.effects import generated_cards
                excluded=[key for key,d in e.CARDS.items() if not d['values'].get('ethereal')]
                for card in generated_cards(state,player['character'],2,exclude=excluded):e.add_generated(state,player,card)
            if 'OrangeDough' in player['relics']:
                from ..combat.effects import generated_cards
                for card in generated_cards(state,'colorless',2):e.add_generated(state,player,card)
            if 'SymbioticVirus' in player['relics']:
                from ..combat.orbs import channel
                channel(state,player,'dark')
            if 'FencingManual' in player['relics']:
                from ..combat.classes.regent import forge
                forge(state,player,10)
            if 'DivineDestiny' in player['relics']:
                from ..combat.classes.regent import gain_stars
                gain_stars(state,player,7)
            if 'InfusedCore' in player['relics']:
                from ..combat.orbs import channel
                channel(state,player,'lightning',3)
            if 'Bread' in player['relics']:player['energy']=max(0,player['energy']-2)
            if 'RunicCapacitor' in player['relics']:
                from ..combat.orbs import change_capacity
                change_capacity(player,3)
        if player['hp']>0 and player.get('turnNumber')==1 and 'Akabeko' in player['relics']:
            e.power(player,'vigor',8)


def after_player_turn_start(state,player):
    if 'GamblingChip' in player['relics'] and player.get('turnNumber')==1:
        from ..run.events.ancient_relics import select_cards
        from ..combat.classes.silent import discard
        cards=select_cards(state,player,list(player['hand']),0,len(player['hand']),'赌博筹码：选择任意数量手牌弃掉并重抽')
        discard(state,player,cards,len(cards))
    if 'ChoicesParadox' in player['relics'] and player.get('turnNumber')==1:
        from ..combat.effects import generated_cards, select_now
        cards=generated_cards(state,player['character'],5)
        for card in cards:card.setdefault('addedKeywords',[]).append('retain')
        select_now(state,player,{'op':'select','source':'generated','destination':'hand','cards':cards,'minimum':1,'maximum':1,'title':'选择悖论：选择一张保留牌'})
    if 'VexingPuzzlebox' in player['relics'] and player.get('turnNumber')==1:
        from ..combat.effects import generated_cards
        from ..combat.costs import free
        for card in generated_cards(state,player['character'],1):free(card);e.add_generated(state,player,card)
    if 'ToastyMittens' in player['relics']:
        from ..combat.effects import select_now
        select_now(state,player,{'op':'select','source':'hand','destination':'exhaust','cards':list(player['hand']),'minimum':1,'maximum':1,'title':'烘焙手套：消耗一张手牌'})
        e.power(player,'strength',1)
    if 'EmotionChip' in player['relics'] and player.get('emotionChipLast'):
        from ..combat.orbs import trigger
        for orb in list(player.get('orbs',[])):trigger(state,player,orb)
    if player.get('turnNumber')==1 and 'Bellows' in player['relics']:
        for card in player['hand']:
            if e.upgradable(card):e.upgrade(card)
    if player.get('turnNumber')==1 and 'FestivePopper' in player['relics']:
        for enemy in list(state['enemies']):
            if enemy['hp']>0:e.hit(state,player,enemy,9,True)
    if 'MrStruggles' in player['relics']:
        for enemy in list(state['enemies']):
            if enemy['hp']>0:e.hit(state,player,enemy,player['turnNumber'],True)
    if 'MercuryHourglass' in player['relics']:
        for enemy in list(state['enemies']):
            if enemy['hp']>0:e.hit(state,player,enemy,3,True)
    if player.get('turnNumber',state['turn'])==1 and 'RoyalPoison' in player['relics']:
        e.hit(state,player,player,4,True,unblockable=True)
    if player.get('turnNumber',state['turn'])==1 and consume_tea(player,'BoneTea',1):
        for card in player['hand']:
            if e.upgradable(card):e.upgrade(card)


def after_exhaust(state,player):
    if 'ForgottenSoul' in player['relics']:
        targets=[enemy for enemy in state['enemies'] if enemy['hp']>0]
        if targets:e.hit(state,player,e.random_enemy(state,targets),1,True)
    if 'CharonsAshes' in player['relics']:
        for enemy in list(state['enemies']):
            if enemy['hp']>0:e.hit(state,player,enemy,3,True)


def after_damage_received(state,player,amount):
    if state['phase']!='combat' or amount<=0 or player['hp']<=0:return
    for relic in player['relics']:
        if relic=='CentennialPuzzle' and not player.setdefault('relicCombat',{}).get('centennialPuzzleUsed'):
            player['relicCombat']['centennialPuzzleUsed']=True
            for _ in range(3):e.draw(state,player,1)
        if relic=='SelfFormingClay':e.power(player,'selfFormingClay',3)
        elif relic=='DemonTongue' and state.get('side')=='player' and not player.get('demonTongueTriggered'):
            player['demonTongueTriggered']=True
            e.heal(player,amount)


def after_block_cleared(state,player):
    if 'SparklingRouge' in player['relics'] and player.get('turnNumber')==3:e.power(player,'strength',1);e.power(player,'dexterity',1)
    for key,turn,amount in [('HornCleat',2,14),('CaptainsWheel',3,18)]:
        if key in player['relics'] and player.get('turnNumber')==turn:e.gain_block(state,player,amount,True)
    amount=player['powers'].pop('selfFormingClay',0)
    if amount:e.gain_block(state,player,amount,True)


def after_energy_reset(player):
    if 'FakeVenerableTeaSet' in player['relics'] and player.pop('fakeTeaSetArmed',False):player['energy']+=1
    if 'VenerableTeaSet' in player['relics'] and player.pop('teaSetArmed',False):player['energy']+=2
    if 'ArtOfWar' in player['relics']:
        if player.get('turnNumber',0)>1 and not player.get('artOfWarLastAttack'):player['energy']+=1
        player.pop('artOfWarLastAttack',None);player.pop('artOfWarAttack',None)


def modify_hp_loss(player,amount,*,in_combat):
    for relic in player.get('relics',[]):
        if relic=='TungstenRod':amount=max(0,amount-1)
        elif relic=='BeatingRemnant' and in_combat:amount=min(amount,max(0,20-player.get('beatingRemnantLoss',0)))
    return amount


def scarf_free(player,card):
    return ('BrilliantScarf' in player['relics'] and player.get('brilliantScarfPlays',0)==4
            and any(c['id']==card['id'] for pile in ('hand','inPlay') for c in player.get(pile,[])))
