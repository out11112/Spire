"""Neow's complete option identities and exclusions, independent of effect coverage."""
from ... import engine as e

POSITIVE=['ArcaneScroll','BoomingConch','FishingRod','GoldenPearl','Kaleidoscope',
          'LeadPaperweight','LostCoffer','MassiveScroll','NeowsTorment','NewLeaf',
          'PhialHolster','PreciseScissors','ScrollBoxes','WingedBoots']
CURSED=['CursedPearl','DowsingRod','HeftyTablet','LargeCapsule','LeafyPoultice',
        'NeowsBones','NeowsSacrifice','PrecariousShears','SilkenTress','SilverCrucible']
EXCLUSIONS={'CursedPearl':{'GoldenPearl'},'HeftyTablet':{'ArcaneScroll'},
            'LeafyPoultice':{'NewLeaf'},'PrecariousShears':{'PreciseScissors'},
            'NeowsSacrifice':{'PhialHolster','LostCoffer'}}


def bones_candidates(state):
    all_options=CURSED+POSITIVE+['LavaRock','NeowsTalisman','NutritiousOyster','Pomander','SmallCapsule','StoneHumidifier']
    return [key for key in all_options if key!='NeowsBones' and allowed(state,key)]


def modifier_curses(state):
    from .transforms import POOLS
    excluded={'AscendersBane','BadLuck','CurseOfTheBell','Enthralled','Folly','Greed','PoorSleep','SporeMind'}
    constraint='SingleplayerOnly' if len(state['players'])>1 else 'MultiplayerOnly'
    return sorted(row['key'] for row in POOLS['curse'] if row['key'] not in excluded and row['constraint']!=constraint)


def bones(state,player):
    from ..rewards.custom import required_relics
    keys=e.rewards_rng(state,player,lambda rng:rng.shuffle(bones_candidates(state)))[:2]
    required_relics(state,player,keys)
    e.obtain_card(state,player,e.new_card(state,e.niche_choose(state,modifier_curses(state))))


def allowed(state,key):
    multi=len(state['players'])>1
    return multi if key=='MassiveScroll' else not multi if key in ('WingedBoots','SilverCrucible') else True


def roll(state,player):
    # Neow is an event, so every draw here is on its own stream:
    # runSeed + (shared ? 0 : seat) + hash(Neow).
    from ...rng import streams
    def ev(draw):
        with streams.open(state) as rngs:
            return draw(rngs.event('Neow',streams.seat_of(player)))
    curse=ev(lambda rng:rng.next_item([key for key in CURSED if allowed(state,key)]))
    positives=[key for key in POSITIVE if key not in EXCLUSIONS.get(curse,set())]
    if curse!='LargeCapsule':positives.append(ev(lambda rng:rng.next_item(['LavaRock','SmallCapsule'])))
    positives.append(ev(lambda rng:rng.next_item(['NutritiousOyster','StoneHumidifier'])))
    positives.append(ev(lambda rng:rng.next_item(['NeowsTalisman','Pomander'])))
    return ev(lambda rng:rng.shuffle([key for key in positives if allowed(state,key)]))[:2]+[curse]


def choices(progress):
    return [(key,('获得 '+e.RELICS[key][0]+'：'+e.RELICS[key][1]) if key in e.RELICS
             else key+'（遗物效果尚未实现）') for key in progress['options']]


def scroll_bundles(state,player):
    from ...core.decisions import select
    pool=[d for d in e.reward_pool(player)
          if not (len(state['players'])==1 and d['values'].get('multiplayerOnly'))
          and not (len(state['players'])>1 and d['values'].get('singleplayerOnly'))]
    used=set();bundles=[]
    for index in range(2):
        if player['character']=='defect' and e.rewards_rng(state,player,lambda rng:rng.next_int(100))==0:keys=['Claw']*3
        else:
            keys=[]
            for rarity in ('common','common','uncommon'):
                key=e.rewards_rng(state,player,lambda rng,pool=pool,rarity=rarity:rng.next_item([d['key'] for d in pool if d['rarity']==rarity and d['key'] not in used]))
                keys.append(key);used.add(key)
        cards=[e.new_card(state,key) for key in keys]
        label='；'.join(e.card_view(c)['name']+'：'+e.card_view(c)['description'] for c in cards)
        bundles.append({'id':'bundle:'+str(index),'label':label,'cards':cards})
    selected=select(state,player,'bundle','卷轴盒：选择一组卡牌',bundles)[0]
    for card in selected['cards']:e.obtain_card(state,player,card)
