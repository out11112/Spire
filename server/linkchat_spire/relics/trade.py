"""Source eligibility for relic trades, independent of installed effects."""
from .. import engine as e
from .pool import DATA

# Declarative HasUponPickupEffect identities from the local v0.111.0 reference.
PICKUP=set('''AlchemicalCoffer Astrolabe BigMushroom BloodSoakedRose Byrdpip
CallingBell Cauldron DistinguishedCape DollysMirror DowsingRod ElectricShrymp
EmptyCage FakeLeesWaffle FakeMango FragrantMushroom GnarledHammer GoldenCompass
GoldenPearl HeftyTablet JewelryBox Kaleidoscope Kifuda LeesWaffle LoomingFruit
LostCoffer Mango NeowsSacrifice NeowsTalisman NeowsTorment NewLeaf NutritiousOyster
OldCoin Orrery PaelsTooth PandorasBox Pear PhialHolster PotionBelt PrecariousShears
PreciseScissors PunchDagger RoyalStamp SandCastle SeaGlass SereTalon Strawberry
ToyBox WarPaint Whetstone YummyCookie'''.split())
PETS={'Byrdpip','BoundPhylactery','PhylacteryUnbound'}


def tradable(player,key):
    if key not in DATA or DATA[key]['rarity'] in ('starter','event','ancient'):return False
    if key in PICKUP or key in PETS or key in player.get('meltedRelics',[]):return False
    if key=='MawBank' and player.get('mawBankSpent'):return False
    if key=='WingedBoots' and player.get('wingedBootsUsed',0)>=3:return False
    if key=='LizardTail' and player.get('lizardTailUsed'):return False
    return True


def candidates(player):return [key for key in player['relics'] if tradable(player,key)]


def remove(state,player,key):
    e.require(key in player['relics'] and tradable(player,key),'这件遗物不能交易。')
    player['relics'].remove(key)
    for field in {'Nunchaku':['nunchakuAttacks'],'Girya':['giryaLifts'],'WingedBoots':['wingedBootsUsed'],
                  'MawBank':['mawBankSpent'],'LizardTail':['lizardTailUsed']}.get(key,[]):player.pop(field,None)
    e.log(state,player['name']+' 交出 '+e.RELICS.get(key,(key,''))[0])
