"""Saved, private ancient offers; eligibility and weights precede acquisition."""
from ... import engine as e

KEYS={'Darv','Nonupeipe','Orobas','Pael','Tanx','Tezcatara','Vakuu'}
NONU=['BlessedAntler','BrilliantScarf','DelicateFrond','DiamondDiadem','FurCoat','Glitter','JewelryBox','LoomingFruit','SignetRing']
TANX=['Claws','Crossbow','IronClub','MeatCleaver','Sai','SpikedGauntlets','TanxsWhistle','ThrowingAxe','WarHammer']


def eligible(player,enchantment):
    from ...combat.enchantments import can_enchant
    return sum(bool(can_enchant(c,enchantment,in_deck=True)) for c in player['deck'])


def tome_pool(state,player):
    from .ancient_relics import TRANSCEND
    return [k for k,d in e.CARDS.items() if d['pool']==player['character'] and d['rarity']=='ancient'
            and k not in TRANSCEND.values() and not (len(state['players'])==1 and d['values'].get('multiplayerOnly'))
            and not (len(state['players'])>1 and d['values'].get('singleplayerOnly'))]


def pools(state,player,key):
    """Repeated entries are intentional probability weight, never duplicate offers."""
    if key=='Darv':
        rows=['Astrolabe','BlackStar','CallingBell','EmptyCage','RunicPyramid','SneckoEye']
        if not state.get('clearsPlayerDeck'):rows.append('PandorasBox')
        if state.get('actIndex',0)==1:rows+=['Ectoplasm','Sozu']
        if state.get('actIndex',0)>=1:rows+=['PhilosophersStone','VelvetChoker']
        return [rows]
    if key=='Nonupeipe':return [NONU+(['BeautifulBracelet'] if eligible(player,'Swift')>=4 else [])]
    if key=='Tanx':return [TANX+(['TriBoomerang'] if eligible(player,'Instinct')>=3 else [])]
    if key=='Pael':
        middle=['PaelsWing']
        if eligible(player,'Goopy')>=3:middle.append('PaelsClaw')
        if sum(e.removable(c) for c in player['deck'])>=5:middle.append('PaelsTooth')
        pets={'Byrdpip','PaelsLegion'}
        return [['PaelsFlesh','PaelsHorn','PaelsTears'],middle*2+['PaelsGrowth'],
                ['PaelsEye','PaelsBlood']+([] if pets.intersection(player['relics']) else ['PaelsLegion'])]
    if key=='Tezcatara':
        soup=any(e.definition(c)['rarity']=='basic' and e.definition(c)['values'].get('strike') for c in player['deck'])
        return [['VeryHotCocoa','YummyCookie']+(['NutritiousSoup'] if soup else []),
                ['BiiigHug','Storybook','ToastyMittens'],['GoldenCompass','PumpkinCandle','ToyBox','SealOfGold']]
    if key=='Vakuu':return [['BloodSoakedRose','WhisperingEarring','Fiddle'],
                           ['PreservedFog','SereTalon','DistinguishedCape'],['ChoicesParadox','MusicBox','LordsParasol','JeweledMask']]
    if key=='Orobas':
        from .ancient_relics import TRANSCEND
        from ...relics.hooks import DATA
        third=[]
        if any(DATA[r]['rarity']=='starter' for r in player['relics']):third.append('TouchOfOrobas')
        if any(c['key'] in TRANSCEND for c in player['deck']):third.append('ArchaicTooth')
        return [['ElectricShrymp','GlassEye'],['AlchemicalCoffer','Driftwood','RadiantPearl','SandCastle'],third or ['locked']]
    raise e.InvalidAction('未知古老之民：'+key)


def roll(state,player,key):
    groups=pools(state,player,key);metadata={}
    # An ancient is an event, so its draws come off the event's own stream:
    # runSeed + (shared ? 0 : seat) + hash(entry).
    def ev(draw):
        from ...rng import streams
        from ..map.journey import SHARED_ANCIENTS
        with streams.open(state) as rngs:
            return draw(rngs.event(key,streams.seat_of(player),shared=key in SHARED_ANCIENTS))
    if key=='Darv':
        shuffled=ev(lambda rng:rng.shuffle(list(groups[0])))
        if ev(lambda rng:rng.next_int(2)):
            offers=shuffled[:2]+['DustyTome']
            metadata['dustyTomeCard']=e.rewards_rng(state,player,lambda rng:rng.next_item(tome_pool(state,player)))
        else:offers=shuffled[:3]
    elif key in ('Nonupeipe','Tanx'):offers=ev(lambda rng:rng.shuffle(list(groups[0])))[:3]
    elif key=='Orobas':
        characters=[c for c in player.get('unlockedCharacters',list(e.CHARACTERS)) if c!=player['character']]
        metadata['seaGlassCharacter']=ev(lambda rng:rng.next_item(list(characters))) if characters else player['character']
        from ...rng.mega_random import f32
        groups[0].append('PrismaticGem' if ev(lambda rng:rng.next_float())<f32(0.3333333) else 'SeaGlass')
        offers=[ev(lambda rng,g=group:rng.next_item(list(g))) for group in groups]
    elif key=='Vakuu':offers=[ev(lambda rng,g=group:rng.shuffle(list(g)))[0] for group in groups]
    else:offers=[ev(lambda rng,g=group:rng.next_item(list(g))) for group in groups]
    return {'options':offers,'offerMetadata':metadata}


def choices(progress,player=None):
    rows=[]
    for key in progress['options']:
        if key=='locked':continue
        label='获得 '+e.RELICS[key][0]+'：'+e.RELICS[key][1]
        if key=='DustyTome':
            card={'key':progress['offerMetadata']['dustyTomeCard'],'upgraded':True}
            label+='；预览：'+e.card_view(card)['name']
        if key=='SeaGlass':label+='；职业：'+e.CHARACTERS[progress['offerMetadata']['seaGlassCharacter']]['name']
        if key=='SereTalon' and player is not None and player['maxHp']<=9:label+='；警告：最大生命不足，选择将致死'
        rows.append((key,label))
    return rows


def obtain(state,player,progress,key):
    from ..rewards.custom import finish_nested
    if key=='DustyTome':player['dustyTomeCard']=progress['offerMetadata']['dustyTomeCard']
    if key=='SeaGlass':player['seaGlassCharacter']=progress['offerMetadata']['seaGlassCharacter']
    e.relic(state,player,key)
    finish_nested(state,player)
    progress['chosen']=key
