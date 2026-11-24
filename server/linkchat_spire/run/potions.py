"""Authoritative potion generation, targeting and resumable effects."""
from .. import engine as e
from ..text.battle_log import emit
from ..content.potions import DATA, POTIONS


def capacity(player):return player.get('potionCapacity',3)


def create(state,key):
    e.require(key in DATA,'未知药水。')
    state['serial']+=1
    return {'id':str(state['serial']),'key':key}


def pool_for(character,*,in_combat=False,exclude=()):
    """The drawable potions: the character's own first, then the shared pool.

    ``PotionFactory.GetPotionOptions`` concatenates the character's pool ahead of
    the shared one, and the item pick is index-based, so the order is part of the
    contract — a sorted list draws different potions for the same seed.
    """
    def keep(entry,pool):
        return (entry['pool']==pool and (not in_combat or entry['inCombat'])
                and key not in exclude)
    own=[key for key,d in DATA.items() if d['pool']==character
         and (not in_combat or d['inCombat']) and key not in exclude]
    shared=[key for key,d in DATA.items() if d['pool']=='shared'
            and (not in_combat or d['inCombat']) and key not in exclude]
    return own+shared


def candidates(player,*,in_combat=False,exclude=()):
    return pool_for(player.get('character','ironclad'),in_combat=in_combat,exclude=exclude)


def draw(rng,available,count):
    """``PotionFactory.CreateRandomPotions`` — a rarity roll then an item pick.

    One rarity roll and one item pick per potion, in that order, both off the
    same stream, with the drawn potion removed so it cannot repeat.
    """
    from ..rng.mega_random import f32
    result=[]
    for _ in range(count):
        roll=rng.next_float()
        rarity=('rare' if roll<=f32(0.1) else 'uncommon' if roll<=f32(0.35) else 'common')
        pool=[key for key in available if DATA[key]['rarity']==rarity]
        key=rng.next_item(pool)
        available.remove(key);result.append(key)
    return result


# Where a generated potion's randomness comes from, per the reference: shop
# stock rides the player's Shops stream, a reward rides Rewards, and anything
# generated mid-combat rides the run's combat-potion stream.
GENERATION_SOURCES=('shops','rewards','combat')


def generate(state,player,count=1,*,source='combat',in_combat=False,exclude=()):
    from ..rng import streams
    e.require(source in GENERATION_SOURCES,'未知的药水随机来源。')
    available=candidates(player,in_combat=in_combat,exclude=exclude)
    e.require(all(any(DATA[key]['rarity']==rarity for key in available)
                  for rarity in ('common','uncommon','rare')) if available else False,
              '药水候选池已耗尽。')
    with streams.open(state) as rngs:
        if source=='shops':rng=rngs.player(streams.seat_of(player),'Shops')
        elif source=='rewards':rng=rngs.player(streams.seat_of(player),'Rewards')
        else:rng=rngs.run('CombatPotionGeneration')
        keys=draw(rng,available,count)
    return [create(state,key) for key in keys]


def procure(state,player,item):
    if 'Sozu' in player['relics']:return False
    if len(player['potions'])>=capacity(player):return False
    player['potions'].append(item)
    from ..relics.hooks import inventory_changed
    inventory_changed(state,player)
    return True


def reward(state,player,count=1):
    for _ in range(count):
        item=generate(state,player,source='rewards')[0]
        if not procure(state,player,item) and 'Sozu' not in player['relics']:player['pendingPotions'].append(item)


def prevent_death(state,player):
    if player['hp']>0:return False
    item=next((item for item in player.get('potions',[]) if item['key']=='FairyInABottle'),None)
    if not item:
        if 'LizardTail' not in player.get('relics',[]) or player.get('lizardTailUsed'):return False
        player['lizardTailUsed']=True;e.heal(player,max(1,player['maxHp']//2));player.pop('deathHandled',None)
        return True
    emit(state,f"{player['name']} 自动消耗 {POTIONS[item['key']][0]}",'potion',actor=player['id'],potion=item['key'],automatic=True)
    player['potions'].remove(item)
    e.heal(player,max(1,player['maxHp']*3//10));player.pop('deathHandled',None)
    from ..relics.hooks import potion_used
    potion_used(state,player)
    e.log(state,f"{player['name']} 的瓶中精灵阻止了死亡")
    return True


def use(state,owner,item,target_id=None):
    key=item['key'];d=DATA[key];combat=state['phase']=='combat'
    e.require(d['usage']!='Automatic','这瓶药水会自动生效，不能主动使用。')
    e.require(combat or d['usage']=='AnyTime','这瓶药水只能在战斗中使用。')
    e.require(not combat or not owner['done'],'你已结束当前回合。')
    if key=='FoulPotion' and not combat:
        fake=state['phase']=='event' and state.get('event')=='FakeMerchant' and not owner.get('done')
        e.require(fake or state['phase']=='shop','只能向商人使用。')
    target=owner
    if d['target']=='AnyEnemy':
        target=next((x for x in state['enemies'] if x['id']==target_id and x['hp']>0),None)
    elif d['target']=='AnyPlayer':
        target=owner if target_id is None else state['players'].get(str(target_id))
    e.require(target is not None and target['hp']>0,'请选择存活的有效目标。')
    # Remove before effects: a brew or a generated potion may refill this slot.
    # Continuations replay this whole action from its origin, consuming it once.
    emit(state,f"{owner['name']} 使用 {POTIONS[key][0]} → {target['name']}",'potion',actor=owner['id'],target=target['id'],potion=key,automatic=False)
    owner['potions'].remove(item)
    from ..relics.hooks import inventory_changed
    inventory_changed(state,owner)
    from ..combat.classes.boss import face
    face(owner,target)
    effect(state,owner,target,key)
    from ..relics.hooks import potion_used
    potion_used(state,owner)
    e.log(state,f"{owner['name']} 使用 {POTIONS[key][0]}")
    e.after_card(state)


def select(state,player,source,destination,*,count=1,minimum=None,title='选择一张牌',**options):
    from ..combat.effects import select_now
    select_now(state,player,dict(op='select',source=source,destination=destination,
        minimum=count if minimum is None else minimum,maximum=count,title=title,**options))


def effect(state,owner,target,key):
    from ..combat.effects import generated_cards, select_now
    from ..combat import orbs, osty
    from ..combat.classes.regent import gain_stars, forge
    powers={'StrengthPotion':('strength',2),'DexterityPotion':('dexterity',2),'FocusPotion':('focus',2),
        'LiquidBronze':('permanentThorns',3),'GhostInAJar':('intangible',1),'HeartOfIron':('plating',7),
        'LuckyTonic':('buffer',1),'MazalethsGift':('ritual',1),'Duplicator':('duplication',1),
        'GigantificationPotion':('gigantification',1),'StableSerum':('retainHand',2),'RegenPotion':('regen',5)}
    if key in powers:e.power(target,*powers[key]);return
    debuffs={'WeakPotion':('weak',3),'VulnerablePotion':('vulnerable',3),'PoisonPotion':('poison',6),
             'PotionOfDoom':('doom',33),'BeetleJuice':('shrink',4),'PowderedDemise':('demise',9)}
    if key in debuffs:e.debuff(state,owner,target,*debuffs[key]);return
    if key in ('FirePotion','PotionShapedRock'):e.hit(state,owner,target,20 if key=='FirePotion' else 15,True);return
    if key in ('BloodPotion','Ambergris'):
        e.heal(target,target['maxHp']//(5 if key=='BloodPotion' else 2))
        if key=='Ambergris' and state['phase']=='combat':e.power(target,'ambergris',1)
    elif key=='FruitJuice':target['maxHp']+=5;e.heal(target,5)
    elif key=='BlockPotion':e.gain_block(state,target,12,True)
    elif key=='EnergyPotion':target['energy']+=2
    elif key=='StarPotion':gain_stars(state,target,3)
    elif key=='PotionOfCapacity':orbs.change_capacity(target,2)
    elif key=='EssenceOfDarkness':orbs.channel(state,target,'dark',target.get('orbCapacity',0))
    elif key=='SwiftPotion':e.draw(state,target,3)
    elif key in ('FlexPotion','SpeedPotion'):
        power='strength' if key=='FlexPotion' else 'dexterity'
        e.power(target,power,5);e.power(target,'potionTemporary'+power.title(),5)
    elif key=='BoneBrew':osty.summon(state,target,15)
    elif key=='KingsCourage':forge(state,target,15)
    elif key=='Fortifier':e.gain_block(state,target,target['block']*2,True)
    elif key in ('AttackPotion','SkillPotion','PowerPotion','ColorlessPotion'):
        kind=None if key=='ColorlessPotion' else key.removesuffix('Potion').lower()
        pool='colorless' if kind is None else target.get('character','ironclad')
        cards=generated_cards(state,pool,3,kind=kind)
        select(state,target,'generated','hand',minimum=0,cards=cards,free=True,creator=owner['id'],title='药水：选择一张牌，本回合免费；可跳过')
    elif key=='CunningPotion':
        for _ in range(3):
            card=e.new_card(state,'Shiv');e.add_generated(state,target,card,creator=owner);e.upgrade(card)
    elif key=='DistilledChaos':select_now(state,target,{'op':'autoplayDraw','count':3})
    elif key=='LiquidMemories':select(state,target,'discard','hand',free=True,title='液态记忆：取回一张牌，本回合免费')
    elif key=='DropletOfPrecognition':select(state,target,'draw','hand',title='预知水滴：选择一张抽牌堆卡牌')
    elif key=='GamblersBrew':select(state,target,'hand','discard',count=10,minimum=0,activeDiscard=True,drawSelected=True,title='赌徒特酿：选择弃掉的手牌')
    elif key=='BlessingOfTheForge':
        for card in target['hand']:
            if e.upgradable(card):e.upgrade(card)
    elif key=='BottledPotential':
        target['draw']+=target['hand'];target['hand']=[];e.shuffle_draw(state,target);e.draw(state,target,5)
    elif key=='SneckoOil':
        e.draw(state,target,7)
        for card in target['hand']:
            values=e.definition(card)['values']
            base=e.CARDS[card['key']]
            base_cost=base['cost']+(base['upgrade'].get('cost',0) if card.get('upgraded') else 0)+card.get('baseCostAdjustment',0)
            if not values.get('xCost') and base_cost>=0:
                amount=e.roll_energy_cost(state);e.change_cost(card,amount,expires=('turn','play'));card['potionTurnCost']=amount;card.pop('freeThisTurn',None)
    elif key=='EntropicBrew':
        while len(target['potions'])<capacity(target):
            if not procure(state,target,generate(state,target,source='combat')[0]):break
    elif key in ('Ashwater','GlowwaterPotion'):
        if key=='Ashwater':select(state,target,'hand','exhaust',count=10,minimum=0,title='灰水：选择任意手牌消耗')
        else:
            for card in list(target['hand']):e.exhaust(state,target,card)
            e.draw(state,target,10)
    elif key=='Clarity':e.draw(state,target,1);e.power(target,'clarity',3)
    elif key=='CosmicConcoction':
        for card in generated_cards(state,'colorless',3):e.upgrade(card);e.add_generated(state,target,card,creator=owner)
    elif key=='CureAll':target['energy']+=1;e.draw(state,target,2)
    elif key=='FyshOil':e.power(target,'strength',1);e.power(target,'dexterity',1)
    elif key=='OrobicAcid':
        cards=[]
        for kind in ('attack','skill','power'):cards+=generated_cards(state,target.get('character','ironclad'),1,kind=kind)
        for card in cards:e.free_card(card);e.add_generated(state,target,card,creator=owner)
    elif key=='PotOfGhouls':
        for _ in range(2):e.add_generated(state,target,e.new_card(state,'Soul'),creator=owner)
    elif key in ('ExplosiveAmpoule','PotionOfBinding','ShacklingPotion'):
        targets=[x for x in state['enemies'] if x['hp']>0]
        if key=='ExplosiveAmpoule':
            for enemy in targets:e.hit(state,owner,enemy,10,True)
        elif key=='PotionOfBinding':
            for power in ('weak','vulnerable'):
                for enemy in targets:e.debuff(state,owner,enemy,power,1)
        else:
            for enemy in targets:
                if e.debuff(state,owner,enemy,'shacklingPotion',7):e.power(enemy,'strength',-7)
    elif key=='RadiantTincture':target['energy']+=1;e.power(target,'radiance',3)
    elif key=='ShipInABottle':e.gain_block(state,target,10,True);e.power(target,'blockNextTurn',10)
    elif key=='SoldiersStew':
        from ..combat.classes.defect import combat_cards
        for card in combat_cards(state,target):
            if e.definition(card)['values'].get('strike'):card['extraReplays']=card.get('extraReplays',0)+1
    elif key=='TouchOfInsanity':
        def costs_resources(card):
            definition=e.definition(card);values=definition['values']
            energy=not values.get('xCost') and (definition['cost']>0 or e.energy_cost(state,target,card)>0)
            local_stars=0 if any(card.get(key) for key in ('freeThisTurn','freeStarsThisTurn','freeThisCombat')) else values.get('starCost',0)
            stars=not values.get('starX') and (local_stars>0 or e.star_cost(target,card)>0)
            return energy or stars
        cards=[card for card in target['hand'] if costs_resources(card)]
        select(state,target,'hand','freeCombat',cards=cards,title='疯狂之触：选择本场免费的手牌')
    elif key=='FoulPotion':
        if state['phase']=='combat':
            for creature in list(state['players'].values())+list(state['enemies']):e.hit(state,owner,creature,12,True)
        elif state.get('event')=='FakeMerchant' and state['phase']=='event':
            from .events.events import fight_fake_merchant
            fight_fake_merchant(state,owner)
        else:e.gain_gold(state,owner,100)
    else:raise e.InvalidAction('药水效果尚未实现：'+key)


def after_energy_reset(state,player):
    if player['powers'].get('radiance'):player['energy']+=1;e.power(player,'radiance',-1)


def before_side_end(state,player):
    if player['hp']>0 and player['powers'].get('regen'):
        e.heal(player,player['powers']['regen']);e.power(player,'regen',-1)


def side_end(state,creature):
    if creature['hp']<=0:return
    if creature['powers'].get('shacklingPotion'):e.power(creature,'strength',creature['powers'].pop('shacklingPotion'))
    if creature['powers'].get('shrink',0)>0:e.power(creature,'shrink',-1)
    if creature['powers'].get('demise'):e.hit(state,creature,creature,creature['powers']['demise'],True,unblockable=True)
    if creature['hp']>0 and creature['powers'].get('ritual'):
        if creature.pop('ritualFresh',False):pass
        else:e.power(creature,'strength',creature['powers']['ritual'])
    creature['powers'].pop('duplication',None)
    for pile in ('hand','draw','discard','exhaust'):
        for card in creature.get(pile,[]):e.expire_cost(card,'turn');card.pop('potionTurnCost',None)
