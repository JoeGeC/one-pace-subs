#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translation script for [One Pace][157-159] Alabasta 02 [1080p].ass
Translates English subtitles to Traditional Chinese (zh-TW)
"""

import re

INPUT_FILE = "/Users/joebarker/Videos/One Pace Subs/12 Alabasta/[One Pace][157-159] Alabasta 02 [1080p].ass"
OUTPUT_FILE = "/Users/joebarker/Videos/One Pace Subs/12 Alabasta/[One Pace][157-159] Alabasta 02 [1080p] zh-TW.ass"

TRANSLATABLE_STYLES = {
    "Main-207-",
    "Secondary-207-",
    "Thoughts-207-",
    "Note-207-",
    "Title-207-",
    "RogerMonologue",
    "Captions-207-",
}

# Regex to strip editor comment blocks from text field
# Matches: {OG}, {Rin: ...}, {Zenef: ...}, {Z}, {So this is... - OG}, {-san}, {-chan}, etc.
# BUT preserve ASS formatting tags like {\i1}, {\fad(...)}, {\pos(...)}, etc.
# Editor comments are identified as {content} where content does NOT start with a backslash
EDITOR_COMMENT_RE = re.compile(r'\{(?!\\)[^}]*\}')

# Captions text translations (exact text portion replacements)
CAPTIONS_TEXT_MAP = {
    r"Nanohana\NKingdom of Alabasta": r"納諾哈那\N阿拉巴斯坦王國",
    r"The Port of Nanohana,\NThe Kingdom of Alabasta": r"納諾哈那港\N阿拉巴斯坦王國",
    r"Commander Portgas D. Ace\NSecond Division\NWhitebeard Pirates": r"波特卡斯·D·艾斯 隊長\N第二隊\N白鬍子海賊團",
    r"On the Outskirts\Nof Nanohana": r"納諾哈那城郊",
    r"Full\NFledged": r"正式\N成員",
}

# Full translation dictionary (English text -> Traditional Chinese)
TRANSLATION_MAP = {
    # Roger monologue
    "Inherited will...": "繼承的意志……",
    r"the tides of time,\Nand humanity's dreams...": r"時代的波流，\N以及人類的夢想……",
    "They cannot be stopped.": "這些都是無法阻止的。",
    "As long as people seek freedom,": "只要人們追尋自由，",
    "these things will never cease to be.": "這些事物便永遠不會消逝。",

    # Title card
    "Landfall in Alabasta": "登陸阿拉巴斯坦",

    # Main dialogue (lines 30-501)
    "So this is one of Alabasta's cities?": "這就是阿拉巴斯坦的城鎮嗎？",
    "Food!": "食物！",
    "Listen, guys!": "大家聽好！",
    r"Practice self-control\Ninstead of acting on instinct!{Z}": r"要懂得克制自己，\N不要只憑本能行動！{Z}",
    r"Practice self-control\Ninstead of acting on instinct!": r"要懂得克制自己，\N不要只憑本能行動！",
    "Yes, Nami!": "是，娜美！",
    r"The guy who most needed\Nto hear that is already gone.": r"最需要聽這句話的人\N早就跑掉了。",
    "Food place!": "有吃的！",
    "Get back here!": "快回來！",
    "Nothing but instinct.": "完全憑本能行動。",
    "What should we do?": "我們該怎麼辦？",
    "Don't worry.": "別擔心。",
    r"Find the biggest commotion,\Nand he'll be there.": r"找最混亂的地方，\N就能找到他。",
    "Bingo.": "沒錯。",
    r"Ugh! He needs to be more aware\Nof that bounty on his head,": r"啊！他難道不知道\N自己的頭上有懸賞嗎，",
    r"{\i1}especially{\i0} in a big country like this!": r"{\i1}偏偏{\i0}在這麼大的國家！",
    r"Don't worry about him.\NLet's just eat first.": r"不管他了。\N我們先吃東西吧。",
    "We'll strategize more after that.": "吃完再說。",
    "They're all the same...": "都是一樣的人……",
    "What's wrong?": "怎麼了？",
    r"{\fad(500,0)}Mr. 3's ship!": r"{\fad(500,0)}這是三先生的船！",
    r"That creep didn't kick\Nthe bucket after all?!": r"那傢伙果然還沒死？！",
    "No mistaking it!": "絕對沒錯！",
    r"His ship runs on the power\Nof his Wax-Wax Fruit!": r"那艘船是靠他的\N蠟蠟果實的能力運作的！",
    "The bastard's here?": "那混蛋在這裡？",
    "This is bad.": "糟了。",
    r"Hey! What's going on?\NWhat happened?": r"喂！怎麼了？\N發生什麼事？",
    r"Oh. It seems someone\Nkeeled over in that restaurant.{Zenef: \"keeled over\" is more fun, and it already has the connotation of being sudden. Now it fits the next line better.}": r"哦。似乎有人\N在那家餐廳倒下了。",
    r"Oh. It seems someone\Nkeeled over in that restaurant.": r"哦。似乎有人\N在那家餐廳倒下了。",
    "Keeled over?!": "倒下了？！",
    r"He seems to have died in the middle\Nof a conversation with the proprietor!": r"他好像是在和店主談話時\N突然死去的！",
    "He's an out-of-towner.": "他是外地人。",
    r"We think he unwittingly ate\NA desert strawberry while traveling.": r"我們猜測他在旅途中\N不小心誤食了沙漠草莓。",
    "A desert strawberry?": "沙漠草莓？",
    r"They're poisonous spiders that\Nlook like red strawberries.": r"那是一種看起來像\N紅草莓的毒蜘蛛。",
    r"Eat one by accident, and you'll\Nsuddenly drop dead a few days later.": r"一旦不小心吃到，\N幾天後便會突然暴斃。",
    r"Contagious poison spreads through\Nthe corpse for a few hours after that,": r"之後幾個小時內，\N死者的屍體會散發傳染性毒素，",
    "so nobody can get close.": "所以沒有人能靠近。",
    r"In the desert, what you\Ndon't know can kill you.": r"在沙漠中，\N無知可以要你的命。",
    r"Just look! The way he's stuck\Nin that position, still holding the meat,{Z}": r"你看！他就這樣保持著\N那個姿勢，手裡還握著肉，{Z}",
    r"Just look! The way he's stuck\Nin that position, still holding the meat,": r"你看！他就這樣保持著\N那個姿勢，手裡還握著肉，",
    r"is proof of just how powerful\Nthe desert strawberry's poison is!": r"正是沙漠草莓毒性\N有多強大的證明！",
    "He came back to life!": "他復活了！",
    "A-Are you all right?": "你、你還好嗎？",
    "Oh, my bad.": "哦，不好意思。",
    "I dozed off.": "我剛才睡著了。",
    r"– That was dozing off?!\N– That was dozing off?!": r"– 那叫做打盹？！\N– 那叫做打盹？！",
    r"R-Ridiculous! You were in the middle\Nof a conversation and a meal!": r"荒、荒唐！你明明正在\N說話、吃飯的當中！",
    "And he's right back to eating!": "他又開始吃了！",
    "So what's the big fuss?": "搞什麼，這麼大聲幹嘛？",
    r"– We were worried you'd died!\N– We were worried you'd died!": r"– 我們還以為你死了！\N– 我們還以為你死了！",
    r"Is this restaurant known\Nfor comedy routines?": r"這家餐廳\N以搞笑聞名嗎？",
    r"No, it's not like that.\NBut we're glad you're okay.": r"不是的，不是那樣。\N但是很慶幸你沒事。",
    r"– Hey! Don't just pass out again!\N– Hey! Don't just pass out again!": r"– 喂！不許再倒下去！\N– 喂！不許再倒下去！",
    "Huh? So he wasn't really dead?": "咦？那他根本沒死？",
    "Just a false alarm.": "虛驚一場。",
    "That hit the spot!": "吃得真飽！",
    "Say, Mister...": "請問老闆……",
    "Yeah?!": "什麼？！",
    "You seen this guy in town?": "你在城裡見過這個人嗎？",
    "He's a pirate with a straw hat...": "他是個戴草帽的海賊……",
    r"You've got a lot of guts\Neating out in public,": r"你居然敢大搖大擺地\N在外面吃飯，",
    r"Second Division commander\Nof the Whitebeard Pirates...": r"白鬍子海賊團\N第二隊隊長……",
    "Portgas D. Ace.": "波特卡斯·D·艾斯。",
    r"Wh-Whitebeard?!\N{\i1}The{\i0} Whitebeard Pirates?!": r"什、白鬍子？！\N{\i1}那個{\i0}白鬍子海賊團？！",
    r"That numbskull is one of\Nthe Whitebeard Pirates?!": r"那個傻瓜是\N白鬍子海賊團的人？！",
    r"You know, I recognize\Nthe tattoo on his back!": r"說起來，我認得\N他背上的刺青！",
    r"That's the mark\Nof the Whitebeard Pirates!": r"那是\N白鬍子海賊團的記號！",
    "What's he doing here?!": "他來這裡幹什麼？！",
    r"What's a famous, big-shot pirate\Ndoing in this country?": r"大名鼎鼎的大海賊\N來這個國家做什麼？",
    "Just looking...": "只是找人……",
    "for my kid brother!": "找我弟弟！",
    "Food pla-a-a-a-a-ace!": "有吃的地方——！",
    r"What's that? There's\Na weird smell in the air!": r"什麼東西？\N空氣中有奇怪的氣味！",
    "Oh! Found it! A food place!": "哦！找到了！有吃的地方！",
    "So? What do you want from me?": "所以呢？你想對我怎樣？",
    "To let me capture you quietly.": "希望你乖乖讓我逮捕你。",
    "Sorry. No can do.": "抱歉，那不行。",
    "Yeah, I figured.": "嗯，也是。",
    r"I'm in the middle\Nof locating another pirate.": r"我正在\N追查另一個海賊。",
    r"Cards on the table,\NI'm not here for your head.": r"坦白說，\N我今天不是來抓你的。",
    "So look the other way.": "那就睜一隻眼閉一隻眼吧。",
    "No can do.": "那不行。",
    "See, I'm a Marine...": "因為我是海軍……",
    "and you're a pirate.": "而你是海賊。",
    "What a silly reason.": "真是個無聊的理由。",
    "Let's have some fun then.": "那就好好玩吧。",
    r"{\fad(150,150)}Gum-Gum...": r"{\fad(150,150)}橡膠橡膠……",
    r"{\fad(150,150)}Rocket!": r"{\fad(150,150)}火箭！",
    "A food place! I finally found one!": "有吃的地方！我終於找到了！",
    "Time to eat! I'm starving!": "開吃！我餓死了！",
    r"Old guy! Food! Food! Food!\NOn the double!": r"老頭！食物！食物！食物！\N快點！",
    r"Hurry! Hurry! Hurry!\NFood! Food! Food!": r"快！快！快！\N食物！食物！食物！",
    "Wow!": "哇！",
    "These are beautiful!": "真漂亮！",
    "I love these kinds of clothes!": "我最喜歡這種衣服了！",
    r"While I realize I asked you\Nto shop for us, Sanji,": r"雖然我確實請你\N幫我們買衣服，山治，",
    "aren't these outfits for dancer girls?": "但這些不是舞女穿的嗎？",
    "And they look amazing on you!": "而且穿在你們身上真的很好看！",
    r"{\q2}I asked for ordinary civilian clothes...": r"{\q2}我說的是普通的平民服裝……",
    r"{\q2}Dancers are civilians too!": r"{\q2}舞女也是平民！",
    "But we have to cross a desert...": "但是我們要穿越沙漠……",
    "Don't worry!": "沒問題！",
    "If you get tired, I'll carry you!": "如果你累了，我來抱你！",
    "Truly a lost cause.": "真是無可救藥。",
    r"But, compared to them, you guys\Nlook like a couple of bandits.": r"不過，跟她們比，\N你們兩個看起來像土匪。",
    "What, and you don't?": "你自己又怎麼樣？！",
    "Chopper!": "喬巴！",
    "What are you doing?": "你在做什麼？",
    "It reeks.": "好臭。",
    "That reminds me, where did you go?": "說起來，你去哪裡了？",
    "Various places!": "到處走走！",
    "Is he feeling ill?": "他是不舒服嗎？",
    "Oh, the perfume's getting to him.": "哦，是香水的氣味讓他不舒服。",
    "Perfume?": "香水？",
    "Oh, right! Tony has a sensitive nose!": "哦，對了！東尼的鼻子特別靈！",
    r"– Oh, this...\N– They are often very potent.": r"– 哦，這個……\N– 香水的氣味往往很濃烈。",
    "Like this?": "像這樣嗎？",
    "Ahh! Stop!": "啊！停！",
    "My love greatly deepens, Mellorine!": "我對你的愛更加深了，美味蕾！",
    "You always this idiotic?": "你一直都這麼蠢嗎？",
    "Huh?!": "什麼？！",
    r"In any case, we've accomplished\Nour first goal of gathering supplies!": r"總之，我們已經完成\N第一個目標——採買補給！",
    "Yes...": "是的……",
    r"We're going to a place\Ncalled Yuba, was it?": r"我們要去的地方\N叫做優芭，對吧？",
    r"That's right, but going there\Nmeans crossing the desert.": r"是的，但是去那裡\N必須穿越沙漠。",
    "So good! The food here is tasty!": "太好吃了！這裡的食物真好吃！",
    "Y-Yeah. Thanks. But...": "是、是啊。謝謝。但是……",
    r"Well, you... ought to\Nscram while you can.": r"這個……你們最好\N趁現在趕快逃。",
    "How come?": "為什麼？",
    "Why, you...!": "你這……！",
    "Who the hell did this?!": "是誰幹的？！",
    "What the hell?!": "這是什麼？！",
    "What's the big idea?!": "搞什麼？！",
    r"Oh! Apologies\Nfor disturbing your meal!": r"哦！打擾各位用餐，\N十分抱歉！",
    r"What idiot would do\Nsomething this crazy?!": r"什麼傻瓜\N會幹出這種蠢事？！",
    "Lu...!": "路……！",
    "Hey! Luf–": "喂！路——",
    "Straw Hat!": "草帽！",
    "I've been looking for you, Straw Hat!": "我一直在找你，草帽！",
    "So you actually came to Alabasta!": "你真的來阿拉巴斯坦了！",
    "Stop eating!": "不許吃了！",
    r"{\fad(0,660)}Isn't he...?": r"{\fad(0,660)}他是不是……？",
    r"You're that smoke guy!\NWhat are you doing here?!": r"你是那個煙男！\N你在這裡幹什麼？！",
    "Why you...!": "你這……！",
    "Hold it!": "站住！",
    "Thanks for the meal!": "多謝款待！",
    "Huh?": "咦？",
    "Wait, Luffy! It's me!": "等一下，路飛！是我！",
    "Hey! Wait up! Hey! Luffy!": "喂！等一下！喂！路飛！",
    "They didn't pay...": "他們沒付錢……",
    r"This is bad! My Gum-Gum moves\Ndon't work on that guy at all!": r"糟了！我的橡膠技\N對那個人完全無效！",
    "Gotta just run for now!": "現在只能先跑！",
    "Tashigi!": "塔西姬！",
    r"Y-Yes, Captain Smoker?!\NDo you need a towel?": r"是、是的，煙薰上尉？！\N您需要毛巾嗎？",
    "This place sure is hot!": "這地方真熱！",
    "Get him! It's Straw Hat!": "追他！是草帽！",
    "Straw Hat?!": "草帽？！",
    "I'll stop him!": "我去攔住他！",
    "Tashigi! Round up the Marines!": "塔西姬！集合所有海軍！",
    r"Search every nook and cranny\Nfor Straw Hat's crew!": r"把這座城的每個角落\N都搜查草帽的同夥！",
    "Yes, sir!": "是！",
    "People with powers are fighting!": "能力者在打架！",
    "Whoa!": "哇！",
    "Straw Hat's crew! That means...": "草帽的同夥！那就是說……",
    "Roronoa Zoro is in this city!": "羅羅諾亞·索隆就在這座城市！",
    r"{\fad(150,150)}White Snake!": r"{\fad(150,150)}白蛇！",
    "Where could Luffy have gone?": "路飛會去哪裡呢？",
    r"Honestly! It's as if our\Ncaptain needs a babysitter!": r"真的！我們的船長\N根本需要人保姆！",
    "Oh! Nami!": "哦！娜美！",
    "Hey, now! This is bad!": "喂！這可不妙！",
    r"Big trouble's brewing\Nif we don't make tracks soon.": r"如果我們不趕快行動，\N就要大麻煩了。",
    "Big trouble?": "大麻煩？",
    "The Marines are here.": "海軍來了。",
    "The Marines?!": "海軍？！",
    r"The sooner we find Luffy,\Nthe sooner we leave town!": r"我們越早找到路飛，\N就能越早離開這座城！",
    "Hey! Hide!": "喂！躲起來！",
    r"– What for?!\N– What is it?!": r"– 為什麼？！\N– 怎麼了？！",
    "The Marines!": "是海軍！",
    "There seems to be a big commotion!": "好像發生了很大的騷動！",
    "Don't let him escape! After him!": "別讓他逃！追！",
    r"Some idiot pirate must be\Nrunning around town or something.": r"大概是哪個笨蛋海賊\N在城裡亂跑吧。",
    "Get back here, Straw Hat!": "給我站住，草帽！",
    r"– It was {\i1}you{\i0}?!\N– It was {\i1}you{\i0}?!{Z}": r"– 是{\i1}你{\i0}？！\N– 是{\i1}你{\i0}？！{Z}",
    r"– It was {\i1}you{\i0}?!\N– It was {\i1}you{\i0}?!": r"– 是{\i1}你{\i0}？！\N– 是{\i1}你{\i0}？！",
    r"Hey, Zoro!{Z}": r"喂，索隆！{Z}",
    r"Oh?! So that's where everyone is?!{Z}": r"哦？！大家都在那裡？！{Z}",
    "You idiot! Ditch those guys first!": "你這笨蛋！先甩掉那些人！",
    r"It's the Straw Hat crew! Over there!{Z}": r"是草帽的同夥！在那裡！{Z}",
    "Okay, so... what now?": "好，那……現在怎麼辦？",
    r"– We run, obviously!\N– Hurry! To the ship!": r"– 當然是跑啊！\N– 快！去船上！",
    "What are you doing?! Let's get back!": "你在做什麼？！快回去！",
    "Hey, you!": "喂，你！",
    "Stop! Don't let them escape!": "住手！不許讓他們逃！",
    "Fall back!": "撤退！",
    "Captain!": "上尉！",
    "Straw Hat is mine!": "草帽是我的！",
    r"Wh-Whoa! Here he comes!": r"哇、哇！他來了！",
    r"{\fad(150,150)}White Blow!": r"{\fad(150,150)}白擊！",
    r"You're mine!{Zenef: line needs to be short. Could also have him say \"Got you!\" if that sounds better to you.}": r"你跑不掉！",
    "You're mine!": "你跑不掉！",
    r"{\fad(150,150)}Heat Haze!": r"{\fad(150,150)}炎熱霞！",
    "You, huh?": "是你啊。",
    "Give it up.": "放棄吧。",
    "You may be smoke,": "你是煙，",
    "but I'm fire.": "但我是火。",
    r"We're too evenly matched\Nto settle things between us.": r"我們勢均力敵，\N根本無法分出勝負。",
    "He has devil fruit powers?!": "他有惡魔果實的能力？！",
    "Who is he, anyway?!": "他到底是誰？！",
    "Ace?!": "艾斯？！",
    "You haven't changed a bit, Luffy.": "你一點都沒變，路飛。",
    r"Ace?! Is that you, Ace?!\NYou ate a devil fruit?!": r"艾斯？！是你嗎，艾斯？！\N你吃了惡魔果實？！",
    "Yep! The Flame-Flame Fruit!": "對！火火果實！",
    r"Captain Smoker!\NSecuring the perimeter!": r"煙薰上尉！\N已包圍外圍！",
    r"No time to chat!\NGet moving! I'll catch up!": r"沒時間說話！\N快走！我之後追上你們！",
    "Leave them to me!": "把他們交給我！",
    r"– Go!\N– Let's go!": r"– 走！\N– 走吧！",
    "Y-Yeah!": "好、好！",
    "But, Luffy!": "但是，路飛！",
    "Who is that guy?!": "那個人是誰？！",
    r"{\fad(150,150)}White...": r"{\fad(150,150)}白……",
    r"{\fad(150,150)}Spark!": r"{\fad(150,150)}白閃！",
    "Wh-What is that?!": "那、那是什麼？！",
    "A house fire?": "是房屋著火了嗎？",
    "No, that's no ordinary fire!": "不，那不是普通的火！",
    "What in the world is happening?": "到底發生什麼事了？",
    r"It's a fight between\Nflame and smoke?!": r"這是火與煙的\N戰鬥？！",
    r"He did say he ate\Nthe Flame-Flame Fruit.": r"他說了他吃了\N火火果實。",
    r"But, Luffy! Is that guy really\Nyour older brother?": r"不過，路飛！那個人\N真的是你哥哥嗎？",
    r"Yup! His name's Ace!": r"對！他叫做艾斯！",
    r"That you have a brother\Nisn't what's surprising.": r"你有哥哥這件事\N本身倒不讓人驚訝，",
    "Why would he be in the Grand Line?": "但他怎麼會在偉大航路？",
    "Ace is a pirate.": "艾斯是個海賊。",
    r"He left our island three years\Nbefore me to look for One Piece.": r"他比我早三年\N離開島嶼去尋找航海王。",
    r"– What?!\N– What?!": r"– 什麼？！\N– 什麼？！",
    r"A-Anyway, let's hurry\Nback to the ship!": r"不、不管了！\N我們快回到船上！",
    "Run before they catch up!": "在他們追上來之前跑！",
    r"The path splits here!\nGo left, Usopp! Everyone catch that?!{Z}": r"這裡分岔了！\n烏索普走左邊！大家聽到嗎？！{Z}",
    r"The path splits here!": r"這裡分岔了！",
    r"Go left, Usopp! Everyone catch that?!{Z}": r"烏索普走左邊！大家聽到嗎？！{Z}",
    r"Yes! I'll follow Nami\Nwherever she goes!": r"是！無論娜美去哪裡\N我都跟著！",
    "Enough, pervy cook!": "夠了，色鬼廚師！",
    r"So cool! The fireball's\Neven higher now!": r"太酷了！火球\N竟然更高了！",
    r"A battle of flame and smoke\Nreally is endless.{Z}": r"火與煙的戰鬥\N果然沒有盡頭。{Z}",
    r"But we already knew that.{Z}": r"不過這是意料之中的事。{Z}",
    "Where did the Straw Hats go?": "草帽一夥去哪了？",
    "They're gone!": "他們不見了！",
    "So is Ace! We've lost sight of him!": "艾斯也不見了！我們跟丟了！",
    r"I finally caught up to Straw Hat\Nin the Grand Line,": r"我終於在偉大航路\N追上了草帽，",
    r"but Portgas D. Ace\Njust had to get in the way.": r"但波特卡斯·D·艾斯\N卻非要插一腳。",
    r"Hurry and load the supplies!\NWe're leaving right away!{Z}": r"快把補給品裝上去！\N我們馬上離開！{Z}",
    "Hurry!": "快！",
    "Unfurl the sails!": "升起帆！",
    r"Say... We just got to the island,\Nbut are we already leaving?": r"說……我們才剛上岸，\N就要離開了嗎？",
    r"Yes. This town was only a stopover\Nfor some needed supplies.": r"是的。這座城只是\N採買補給的中途站。",
    r"Next, we sail the ship up the river\Nfarther into Alabasta.": r"接下來，我們要沿著河流\N駛入阿拉巴斯坦的內陸。",
    r"Our next destination is Erumalu,\Nthe City of Green.": r"我們的下一個目的地\N是愛魯瑪魯，翠綠之城。",
    "Erumalu?": "愛魯瑪魯？",
    "Pick up the pace!": "快點！",
    "All set!": "準備好了！",
    "Okay! Let's set sail!": "好！出發！",
    "Huh?": "咦？",
    "Y'know...": "不知道……",
    r"I get the feeling\Nwe're missing someone...": r"總覺得\N少了一個人……",
    "That's weird.": "真奇怪。",
    "Where did they go?": "他們去哪了？",
    r"Man! I guess my letting you escape\Nwas pretty much pointless.": r"嘿！看來我讓你們逃跑\N根本沒有什麼意義嘛。",
    "Hey!": "喂！",
    "Ace!": "艾斯！",
    "Been a while, Luffy.": "好久不見，路飛。",
    "Right back at you, Ace!": "你也是，艾斯！",
    "How many years has it been?": "幾年了啊？",
    "Good question.": "說得是。",
    r"But Luffy, I see you still\Ndo things at your own pace,": r"不過路飛，\N你果然還是我行我素，",
    r"just like when we were kids.": r"和小時候一樣。",
    "You too, Ace!": "你也是，艾斯！",
    r"I'm surprised you ate a devil fruit,\Nbut besides that, you're the same!": r"你吃了惡魔果實讓我很吃驚，\N但除此之外，你一點都沒變！",
    r"Like when you'd sneak into\Nthe fields, eat 100 watermelons,": r"就像你偷偷溜進田裡，\N吃了一百個西瓜，",
    r"and then spit the seeds out\Nlike a gun and run!": r"然後把籽像子彈一樣噴出去\N然後逃跑！",
    "That wasn't me! That was you!": "那不是我！那是你！",
    r"Yeah, and they\Nwhupped you good for it!": r"對，然後\N你被打得很慘！",
    r"Again, that was you!\NI only watched and laughed!": r"說了那是你！\N我只是在旁邊看著笑！",
    "So we didn't change!": "我們果然都沒變！",
    "Nope!": "對！",
    "Brings back memories!": "讓人想起往事！",
    "So...": "說起來……",
    r"weren't your friends\Nlooking for you?": r"你的同夥\N不是在找你嗎？",
    "Yeah.": "嗯。",
    r"But, Ace. What are you\Ndoing in this country?": r"不過，艾斯。\N你在這個國家做什麼？",
    r"You mean, you didn't get\Nthe message I left back in Drum?": r"什麼，你沒收到我\N在德魯姆留下的信息嗎？",
    "Drum?": "德魯姆？",
    r"Yeah. Don't sweat it,\Nthough. No biggie.": r"嗯。不過\N別在意，沒什麼大事。",
    r"I'm in these waters seeing\Nto a minor business matter,": r"我在這附近\N處理一件小事，",
    "so I thought I might look you up.": "所以順便來找你看看。",
    "Minor business?": "小事？",
    r"I joined up with\Nthe Whitebeard Pirates.": r"我加入了\N白鬍子海賊團。",
    "Whitebeard Pirates?": "白鬍子海賊團？",
    r"Here's the mark\Nof a Whitebeard Pirate.": r"這是\N白鬍子海賊的記號。",
    "It's my pride.": "這是我的驕傲。",
    "Oh?": "哦？",
    r"So, Luffy, how 'bout joining\NWhitebeard's crew?": r"那麼，路飛，\N要不要加入白鬍子的船隊？",
    "Your friends can come too.": "你的同夥也可以一起來。",
    "No.": "不。",
    "Oh well, just thought I'd ask.": "嗯，只是隨口問問。",
    r"Whitebeard is the greatest pirate\NI've ever known.": r"白鬍子是我所知道的\N最偉大的海賊。",
    r"{\fad(0,960)}I'm gonna help him\Nbecome King of the Pirates...": r"{\fad(0,960)}我要幫他\N成為海賊王……",
    "It won't be you, Luffy.": "不會是你，路飛。",
    r"That's fine! Then I guess\Nwe gotta fight!": r"沒關係！那我們\N就只能打一場了！",
    "I'm gonna be King of the Pirates.": "我要成為海賊王。",
    "Hey! Don't drink it all, Luffy!": "喂！不許都喝完，路飛！",
    "Something big happening in town?": "城裡發生了什麼大事嗎？",
    r"Smoker and all his men\Nleft the ship.": r"煙薰和他所有的部下\N都離開了船。",
    "But... this is perfect!": "但是……正合我意！",
    "Here's my chance to try and escape!": "這是我逃跑的好機會！",
    "Mr. 11.": "十一先生。",
    r"You know my codename, so you\Nmust be members of Baroque Works!": r"你知道我的代號，\N所以你們一定是蠻好聽成員！",
    "Millions, I take it?": "你們是十億組吧？",
    "Hurry and untie me!": "快給我鬆綁！",
    r"Indeed, we {\i1}are{\i0} members\Nof Baroque Works.": r"我們{\i1}確實{\i0}是\N蠻好聽的成員。",
    r"We're {\i1}billions{\i0}, though.\NWe're next to become number agents.": r"不過我們是{\i1}十億組{\i0}。\N我們是下一批晉升的數字幹部候補。",
    r"Mr. 11, you're barely an agent, seeing\Nas you're not much stronger than us.{Z}": r"十一先生，你頂多算個幹部，\N說實在並沒有比我們強多少。{Z}",
    "O-Oh! I see!": "哦、哦！這樣啊！",
    r"My mistake, billions.\NBut could you hurry and untie me?": r"失禮了，十億組。\N但能不能麻煩你們快點給我鬆綁？",
    "That'd be stupid of us!": "那我們才蠢呢！",
    r"With you gone, one of us will get\Npromoted to a number agent.": r"只要你消失，\N我們之中就有人能晉升為數字幹部。",
    r"So let's empty\None of the agents' seats!": r"那就讓一個數字幹部的\N席位空出來吧！",
    r"{\t(1830,0,1,\c&HFFFFFF&\3c&HFFFFFF&\4c&HFFFFFF&)}W-Wait!": r"{\t(1830,0,1,\c&HFFFFFF&\3c&HFFFFFF&\4c&HFFFFFF&)}等、等一下！",
    "Fire Fist Ace is in this town!": "火拳艾斯在這座城裡！",
    "What?!": "什麼？！",
    "Fire Fist Ace?!": "火拳艾斯？！",
    r"The Second Division commander\Nof the Whitebeard Pirates?": r"白鬍子海賊團\N第二隊隊長？",
    r"{\fad(0,870)\q2}If we can take down Ace,\Nwe're guaranteed to be number agents!": r"{\fad(0,870)\q2}只要能打倒艾斯，\N我們就能保證晉升為數字幹部！",
    "Oh! The ocean!": "哦！大海！",
    "See your ship?": "看到你的船了嗎？",
    "End of the line!": "逃無可逃！",
    "Oh!": "哦！",
    "There it is!": "在那裡！",
    "Hey! Over here! Guys!": "喂！在這裡！大家！",
    "Hey, Luffy. Go on ahe–": "喂，路飛。你先走——",
    "Never mind.": "算了。",
    r"Oh! There he is! It's Luffy!{LOL, Nami's lips aren't moving.}{why was this left in the file now I am cursed with this knowledge as well}": r"哦！他在那裡！是路飛！",
    r"Oh! There he is! It's Luffy!": r"哦！他在那裡！是路飛！",
    "I found Luffy!": "我找到路飛了！",
    r"Where is he?{Z}": r"在哪裡？{Z}",
    r"Yeah. That's definitely his dumb mug.": r"嗯。那張傻臉絕對是他沒錯。",
    "I'm back!": "我回來了！",
    "Sanji! Tony!": "山治！東尼！",
    "Oh, come on!": "拜託了！",
    "Not again.": "又來了。",
    r"Sorry about that, Sanji and Chopper.{Z}": r"抱歉，山治和喬巴。{Z}",
    r"How do you never learn from any\Nof this?! I oughta just gut you here!": r"你怎麼就是不長記性呢？！\N我真想在這裡宰了你！",
    r"Yeah! Do you even realize\Nthe trouble you've caused?!": r"對！你知不知道\N你惹了多大的麻煩？！",
    "Try to act somewhat like a captain!": "你好歹像個船長樣子！",
    "Sorry.": "對不起。",
    "Oh, that's right! Ace!": "哦，對了！艾斯！",
    "Ace?": "艾斯？",
    "Your brother was with you?": "你哥哥和你在一起？",
    "Is it okay to just leave him there?": "就這樣把他留下來沒問題嗎？",
    r"Oh, it's okay! Ace is pretty strong!": r"哦，沒問題！艾斯很強的！",
    "He's strong?": "他很強？",
    r"Yup. Back in the day he hadn't\Neaten the Flame-Flame Fruit,": r"嗯。以前他還沒吃\N火火果實的時候，",
    r"but I still never beat him\Nin a single fight!": r"我也從來沒有\N在打架中贏過他！",
    r"Ace is {\i1}that{\i0} strong!": r"艾斯就是{\i1}那麼{\i0}強！",
    r"There's a flesh-and-blood person\Nyou could never beat?!": r"你是說有個真實存在的人\N讓你從來沒贏過？！",
    r"So the monster's big bro\Nis an even bigger monster.": r"所以怪物的哥哥\N是個更大的怪物。",
    r"That's right! I lost to him all the time!": r"沒錯！我一直輸給他！",
    r"But now, I'd beat him good!": r"但是現在，我一定能打贏他！",
    r"Guessing you've got\Nnothing to base that on.": r"我猜你說這話\N沒有任何根據。",
    "Who...": "什麼……",
    "can beat who now?!": "誰能打贏誰？！",
    r"Oh! Ace! These are\Nthe friends we talked about!": r"哦！艾斯！這些就是\N我說過的同夥！",
    r"Oh! Thank you all for looking\Nafter my kid brother.": r"哦！謝謝大家照顧\N我弟弟。",
    r"– Huh? Oh, not at all.\N– Huh? Oh, not at all.": r"– 咦？哦，不用謝。\N– 咦？哦，不用謝。",
    r"And maybe he's sometimes\Na bit too much to handle, but...": r"他有時候可能讓你們\N費了不少心思，但是……",
    r"– No, not at all.\N– No, not at all.": r"– 不，哪裡的話。\N– 不，哪裡的話。",
    "Take good care of him.": "請多關照他。",
    r"Well, you two\Nprobably want to catch up.": r"那麼，你們兩個\N大概有很多話要說吧。",
    r"Come on in.\NI'll make some tea.": r"請進來吧。\N我去泡茶。",
    r"No, that's okay. Don't trouble\Nyourself on my account.": r"不，沒關係。\N不用特意為我費心。",
    "T-Talk about unexpected...": "這、這真是出乎意料……",
    "That's for sure.": "確實如此。",
    r"I'd have thought he'd be\Nas reckless as Luffy.": r"我還以為他會\N和路飛一樣魯莽。",
    r"There's no way this\Nsensible man is Luffy's brother!{Z}": r"這個理性的人\N怎麼可能是路飛的哥哥！{Z}",
    r"He's nice {\i1}and{\i0} he cares\Nabout his kid brother.": r"他不但人好，\N還很關心他弟弟。",
    "Brothers can be so wonderful!": "兄弟之情真是太美好了！",
    "The sea is just full of surprises.": "大海總是充滿驚喜。",
    "Come now, everyone!": "好了，大家快來！",
    "See! Aren't these guys neat?!": "你看！這些傢伙很有趣吧！",
    r"Baroque Works!\NThose are the billions' ships!": r"蠻好聽！\N那是十億組的船！",
    r"Fire Fist Ace and Straw Hat Luffy!\NDon't think you've gotten away!": r"火拳艾斯和草帽路飛！\N別以為你們逃掉了！",
    r"We'll show you just what\NBaroque Works' billions are made of!": r"讓你們見識見識\N蠻好聽十億組的厲害！",
    "Those guys again?": "又是那些傢伙？",
    r"Luffy. I'll take out the trash.": r"路飛。讓我來清理垃圾。",
    "What's he going to do?": "他要做什麼？",
    "Especially in that little boat...": "就靠那艘小船……",
    r"Let's see the Whitebeard Pirates'\NSecond Division commander in action.{Z}": r"讓我們見識一下\N白鬍子海賊團第二隊隊長的實力。{Z}",
    "Here he comes! Fire Fist Ace!": "他來了！火拳艾斯！",
    r"Just try us, hotshot,\Nbut it's you against five ships!": r"不自量力，\N你一個人對五艘船！",
    "He jumped!": "他跳起來了！",
    "F-Fire!": "開、開火！",
    r"Blast him into a watery grave!": r"把他轟進海裡餵魚！",
    r"{\fad(150,150)}Fire Fist!": r"{\fad(150,150)}火拳！",
    "Woo-hoo!": "耶！",
    "A-Amazing!": "太、太厲害了！",
    "Captain Smoker!": "煙薰上尉！",
    r"Straw Hat Luffy and his crew\Nare nowhere to be found.": r"草帽路飛和他的同夥\N已經找不到人了。",
    r"What do you make of this, Tashigi?": r"塔西姬，你怎麼看？",
    "Vivi was with them.": "薇薇和他們在一起。",
    r"Vivi? Princess Nefertari Vivi\Nwas with the Straw Hats?": r"薇薇？內菲塔利·薇薇公主\N和草帽一夥在一起？",
    "She must be a hostage.": "她一定是人質。",
    r"The princess' abduction\Nmust be part of some plot.": r"公主被綁架\N一定是某個陰謀的一部分。",
    r"No. Vivi was acting like\Nshe was part of their crew.": r"不。薇薇的舉止\N就像是他們的同夥一樣。",
    "The princess? Part of their crew?": "公主？是他們的同夥？",
    r"There's something\Nafoot in this country.": r"這個國家\N有什麼陰謀在進行。",
    "I'm sorry, sir!": "對不起！",
    r"Mr. 11 was done in by someone\Nwhile tied up on the ship!": r"十一先生在船上被綁著的時候\N遭人暗算了！",
    r"We still haven't located\Nthe Straw Hats, either!": r"我們也還沒有\N找到草帽的下落！",
    r"Get it together. I believe\NI know where they're headed.": r"振作起來。我想\N我知道他們要去哪裡。",
    "He's gunning for Crocodile.": "他盯上了克洛克達爾。",
    "Crocodile?!": "克洛克達爾？！",
    "A pirate backed by the government,": "一個受到政府背書的海賊，",
    r"{\q2}one of the Seven Warlords of the Sea?!": r"{\q2}七武海之一？！",
    r"You know I hate\Nthe Seven Warlords, right?": r"你知道我有多討厭\N七武海，對吧？",
    r"{\i1}Especially{\i0} that detestable man.": r"{\i1}尤其是{\i0}那個可憎的傢伙。",
    r"B-But he's currently an ally\Nto the Marines and the government!": r"但、但他現在是\N海軍和政府的盟友！",
    r"He's always been clever, that pirate.": r"那個海賊向來是個聰明人。",
    r"He's not the type to roll over\Nand beg for the government. Not him!": r"他不是那種\N乖乖聽政府話的人！",
    "Tashigi! Remember this one thing!": "塔西姬！記住一件事！",
    r"A pirate's a pirate,": r"海賊就是海賊，",
    r"no matter his status!{Z}": r"無論地位如何！{Z}",
    r"If we head toward Crocodile,\Nwe'll find Straw Hat.": r"只要往克洛克達爾那裡去，\N就能找到草帽。",
    r"It'll all come to light\Nwhen we get there.": r"等我們到了那裡，\N一切都會水落石出。",
    r"And next time, you won't\Nget away, Straw Hat!": r"下次，\N你就別想逃了，草帽！",
    "Yoo-hoo!": "唷！",
    "Ace is one of us now!": "艾斯也是我們的人了！",
    "Cheers!": "乾杯！",
    r"Whad'ya mean, I'm one of you?": r"什麼叫做我是你們的人？",
    r"{\an8}Here's to delicious drinks!": r"{\an8}為好喝的飲料乾杯！",
    r"{\an8}Cheers!": r"{\an8}乾杯！",
    "Medicine is gross!": "藥好難喝！",
    r"{\an8}Medicine is gross!": r"{\an8}藥好難喝！",
    r"Pay it no mind!": r"不用在意！",
    r"They'll find any excuse\Nto have a drink!": r"他們隨便找個藉口\N就要喝酒！",
    "Ace! Are you sure you won't join us?": "艾斯！你真的不加入我們嗎？",
    "I'm chasing a certain man.": "我在追一個人。",
    "His name's Blackbeard.": "他的名字叫黑鬍子。",
    "Blackbeard?": "黑鬍子？",
    r"He's the pirate who attacked\Nthe Kingdom of Drum!": r"他就是那個\N攻擊德魯姆王國的海賊！",
    r"He once belonged\Nto Whitebeard's Second Division,{Z}": r"他曾經屬於\N白鬍子的第二隊，{Z}",
    r"one of my own men.": r"是我手下的人之一。",
    r"But he committed the most\Ngrievous act any pirate could.{Z}": r"但他犯下了\N海賊最不可饒恕的罪行。{Z}",
    r"He killed a crewmate\Nand jumped ship.": r"他殺了一名船員\N然後棄船逃走。",
    r"Since I'm the commander,\NI gotta take responsibility for him.": r"既然我是隊長，\N我就必須對他負責。",
    r"So that's why you're\Nchasing after him?": r"所以這就是\N你追著他的原因？",
    r"We've just started up\Nthe Sandora River.": r"我們剛剛\N進入了桑多拉河。",
    r"First, we'll land at Erumalu.{Z}": r"首先，我們在愛魯瑪魯登陸。{Z}",
    r"We'll then head into Alabasta's\Ninterior to reach Yuba here!": r"然後深入阿拉巴斯坦的內陸\N到達這裡的優芭！",
    r"That's where we'll find\Nthe leader of the Rebellion.": r"反抗軍的首領\N就在那裡。",
    r"I see. Yuba it is then.": r"原來如此。\N那就是優芭了。",
    r"I'll follow Nami and Vivi\Nwherever they go!": r"無論娜美和薇薇去哪裡\N我都跟著！",
    "Drop dead, Love Cook.": "去死吧，愛情廚師。",
    r"Say what?! You–": r"你說什麼？！你——",
    r"A-Anyways! It seems we'll be\Ntraveling together for a bit!": r"不、不管了！\N看來我們暫時要一起行動了！",
    r"Yeah, yeah! His brother is\Nmore than welcome here!": r"好啊好啊！他的哥哥\N我們歡迎之至！",
    "Let's have some fun, Ace!": "我們好好玩吧，艾斯！",
    "Yeah!": "好！",

    # Additional entries for lines that had mismatched case or missing {Z} variants
    r"We think he unwittingly ate\Na desert strawberry while traveling.": r"我們猜測他在旅途中\N不小心誤食了沙漠草莓。",
    "Hey, Zoro!": "喂，索隆！",
    "Oh?! So that's where everyone is?!": "哦？！大家都在那裡？！",
    "It's the Straw Hat crew! Over there!": "是草帽的同夥！在那裡！",
    r"Still, I never thought\NI'd see Ace in a place like this!": r"沒想到\N我竟然在這裡見到艾斯！",
    "Go left, Usopp! Everyone catch that?!": "烏索普走左邊！大家聽到嗎？！",
    r"A battle of flame and smoke\Nreally is endless.": r"火與煙的戰鬥\N果然沒有盡頭。",
    "But we already knew that.": "不過這是意料之中的事。",
    r"Hurry and load the supplies!\NWe're leaving right away!": r"快把補給品裝上去！\N我們馬上離開！",
    r"Mr. 11, you're barely an agent, seeing\Nas you're not much stronger than us.": r"十一先生，你頂多算個幹部，\N說實在並沒有比我們強多少。",
    "Where is he?": "在哪裡？",
    "Sorry about that, Sanji and Chopper.": "抱歉，山治和喬巴。",
    r"There's no way this\Nsensible man is Luffy's brother!": r"這個理性的人\N怎麼可能是路飛的哥哥！",
    r"Let's see the Whitebeard Pirates'\NSecond Division commander in action.": r"讓我們見識一下\N白鬍子海賊團第二隊隊長的實力。",
    "no matter his status!": "無論地位如何！",
    "Here's to delicious drinks!": "為好喝的飲料乾杯！",
    r"He once belonged\Nto Whitebeard's Second Division,": r"他曾經屬於\N白鬍子的第二隊，",
    r"But he committed the most\Ngrievous act any pirate could.": r"但他犯下了\N海賊最不可饒恕的罪行。",
    "First, we'll land at Erumalu.": "首先，我們在愛魯瑪魯登陸。",
}


def strip_editor_comments(text):
    """Remove editor comment blocks like {OG}, {Rin: ...}, {Zenef: ...}, etc.
    Preserve ASS formatting tags that start with backslash."""
    return EDITOR_COMMENT_RE.sub('', text)


def strip_honorifics(text):
    """Remove honorific blocks like {-san}, {-kun}, {-chan}."""
    return re.sub(r'\{-\w+\}', '', text)


def translate_captions_text(text):
    """For Captions-207- lines, only translate known text portions."""
    for en, zh in CAPTIONS_TEXT_MAP.items():
        if en in text:
            text = text.replace(en, zh)
    return text


def translate_line_text(style, raw_text):
    """
    Translate a single dialogue text field.
    Returns the translated text.
    """
    if style == "Captions-207-":
        # Only translate specific text portions in captions, leave complex vector data alone
        return translate_captions_text(raw_text)

    if style == "Title-207-":
        # Title lines have leading ASS formatting tags like {\blur...\fad...\pos...}
        # Extract the leading tag block(s) and translate just the text after them
        # Pattern: one or more {...} blocks at the start, where content starts with backslash
        leading_tags_match = re.match(r'^((?:\{\\[^}]*\})+)(.*)', raw_text, re.DOTALL)
        if leading_tags_match:
            tags = leading_tags_match.group(1)
            text_only = leading_tags_match.group(2).strip()
            if text_only in TRANSLATION_MAP:
                return tags + TRANSLATION_MAP[text_only]
        # Fallback: treat as regular line
        if raw_text in TRANSLATION_MAP:
            return TRANSLATION_MAP[raw_text]
        return raw_text

    # For all other translatable styles: strip editor comments and honorifics, then look up translation
    cleaned = strip_editor_comments(raw_text)
    cleaned = strip_honorifics(cleaned)
    cleaned = cleaned.strip()

    # Look up in translation map
    if cleaned in TRANSLATION_MAP:
        return TRANSLATION_MAP[cleaned]

    # Try without trailing {Z} marker
    if cleaned.endswith('{Z}'):
        base = cleaned[:-3].rstrip()
        if base in TRANSLATION_MAP:
            return TRANSLATION_MAP[base] + '{Z}'

    # Return cleaned text if no translation found (fallback)
    return cleaned


def parse_dialogue_line(line):
    """Parse an ASS Dialogue line into components.
    Returns (prefix, style, text_part) or None if not a Dialogue line."""
    if not line.startswith('Dialogue:'):
        return None

    # Split on commas, but only the first 9 commas (10 fields total)
    # Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    parts = line.split(',', 9)
    if len(parts) < 10:
        return None

    style = parts[3].strip()
    text_part = parts[9]  # Everything after 9th comma, including \n at end
    prefix = ','.join(parts[:9]) + ','

    return (prefix, style, text_part)


def process_file(input_path, output_path):
    """Read input ASS file, translate, and write output."""
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    output_lines = []
    translated_count = 0
    untranslated = []

    for i, line in enumerate(lines):
        line_stripped = line.rstrip('\n\r')

        parsed = parse_dialogue_line(line_stripped)
        if parsed is None:
            # Non-dialogue line: copy verbatim
            output_lines.append(line)
            continue

        prefix, style, text_part = parsed
        # text_part may have trailing \n
        text_content = text_part.rstrip('\n\r')
        line_ending = text_part[len(text_content):]

        if style not in TRANSLATABLE_STYLES:
            # Non-translatable style: copy verbatim
            output_lines.append(line)
            continue

        # Translate
        translated_text = translate_line_text(style, text_content)

        if translated_text == strip_honorifics(strip_editor_comments(text_content)).strip() and style != "Captions-207-":
            # Check if it was already in Chinese or if untranslated
            # Only flag if content is non-empty ASCII-ish text
            if text_content and not any(ord(c) > 127 for c in text_content):
                untranslated.append((i + 1, style, text_content))

        new_line = prefix + translated_text + line_ending + '\n'
        output_lines.append(new_line)
        translated_count += 1

    with open(output_path, 'w', encoding='utf-8-sig') as f:
        f.writelines(output_lines)

    print(f"Processed {translated_count} translatable dialogue lines.")
    if untranslated:
        print(f"\nWARNING: {len(untranslated)} lines may be untranslated (no match found):")
        for lineno, style, text in untranslated[:20]:
            print(f"  Line {lineno} [{style}]: {repr(text[:80])}")
    else:
        print("All translatable lines appear to have been translated successfully.")


if __name__ == '__main__':
    process_file(INPUT_FILE, OUTPUT_FILE)
    print(f"\nOutput written to:\n{OUTPUT_FILE}")
