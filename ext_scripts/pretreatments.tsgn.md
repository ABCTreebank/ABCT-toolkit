# Pretreatment Commands to Keyaki Treebank
変換の第一歩として、Keyaki Treebankの整形を行う。

## 方針
- Keyaki Treebankでのアノテーションの間違いは、予め手で直さなければならない。
- 非終端範疇の追加や変更：それらが行われる場合，
        原則的には，Keyakiの既存範疇（や，範疇の命名規則）に合わせることにする．
- 拡張素性について：＠＠＠
- 終端空範疇の使用：
  - それを付け加えることによりbinary branchingの場合に帰着することで，
        より単純な範疇変換を目指す．
  - 文法関係がマークできる場合（たいてい，`#role=c`，`#role=h`，次の工程を待たずにマークを行うことにする．
  - 空範疇を付け加えることと、unary branchingを作ることは等価であるので、
        本当は（理論的には）どちらでもよい。

## 技術的な注意
- Tsurgeon scriptでは、「検索式-改行-操作の式-改行」が一つのプロシージャになっている。2つの注意点がある。
    - 改行は必須。
    - プロシージャは、検索式を満たす部分木が見つかる限り永遠に実行される（whileループのように）。無限ループが生じやすいので注意。
- 木のルートには，後々のために何かしらのラベルをつけておく．
  いくつかのプログラム（例：NLTK）においては，ノードにラベルがついていない場合，その木を読み込んでくれないことがある．
```tsurgeon
/^$/=root

relabel root /^(.*)$/TOP/

```

## 不要な情報の除去
束縛情報を拡張素性に押し込む．
束縛情報には、
- 項の束縛の情報（例：`NP;*SBJ*`）
- sort information（例：`NP-SBJ;{USAGI}`）

の2つがある．前者は`;`を伴うが，後者では伴うとは限らない．
これらを，拡張素性に変換する．\
前者では遊離数量詞素性`fq`，後者ではsort素性`sort`にもとの情報が書き込まれる．

```tsurgeon
/^(.*)\;\*(.*)\*(.*)$/#1\%cat#2\%fq#3\%rem=x !> ID

relabel x /^.*$/\%{cat}#fq=\%{fq}\%{rem}#role=a/

/^(.*)\;?\{(.*)\}(.*)$/#1\%cat#2\%sort#3\%rem=x !> ID

relabel x /^.*$/\%{cat}#sort=\%{sort}\%{rem}/

```
ICH (Interpret this Constituent Here)とは，音型のある場所と解釈場所が異なるときに用いられる
  アノテーションの方法である．

* 音型のある場所は，`CAT-1`のように，indexが振られる．
* 一方で，解釈場所では， `(CAT-SUBCAT *ICH*-1)`のようなノードがアノテートされる．

このうち，前者の，音型のある場所の情報を，拡張素性に変換する．

```tsurgeon
/(.+)-([0-9]+)$/#1\%cat#2\%ICH=x < __

relabel x /^.*$/\%{cat}#index=\%{ICH}/

```

コメントは削除する。
```tsurgeon
COMMENT=x

delete x

```

括弧の範疇についても，relabelingプログラムのために，変更する．
```tsurgeon
-LRB-=x 

relabel x LRB

-RRB-=x

relabel x RRB

```

### 検討すべきこと
- FS（言い間違い）は削除すべきかどうか？
- PROをDと同等に扱うか？


## 等位接続の正規化
目標：
```
(XP (CONJP (XP 1)
           (CONJ/P 1))
    (CONJP (XP 2)
           (CONJ/P 2))
    ...
    (CONJP (XP n-1)
           (CONJ/P n-1))
    (XP n)
    (CONJ/P n))
->
(XP#deriv=conj (XP 1) 
              (CONJ/P 1)
              (XP 2)
              (CONJ/P 2)
              ...
              (XP n)
              (CONJ/P n))
```

### 検出
まず，等位接続構文を検出し，マークする．

```tsurgeon
__=xp 
  < /^CONJP/ 
  !== /#deriv=/

relabel xp /^.*$/={xp}#deriv=conj/

```

### CONJPの繰り上げ
CONJPを破壊し，中身を繰り上げる．

```tsurgeon
CONJP=conjp > /#deriv=conj/

excise conjp conjp

```


## チャンキングの変更
意味表示を考える際に都合の良いようにチャンキングを変更する．
主にモーダル表現・接続表現が対象である．

### 「はずがない」
```tsurgeon
/^NP/=x  <-2 /^IP/=z <-1 (__=start < はず|筈) $. (__ < が|は|も|の) > (PP=y $. (__=w < /\*/ $. (__=end < ない|なかろ|なかっ|あろ|あり|ある)))

excise x x
excise y y
excise z z
delete w
createSubtree MD start end

MD < (__=x < __)

excise x x

__=x $ __=y !< __

relabel x /^.*$/={x}={y}/
delete y

```

### 「はずがありません」
```tsurgeon

MD  < /^(はず|筈)(が|は|も)あり$/=x  $. ((AX=y < ませ) $. (NEG=z < ん|ぬ=w))

delete y
relabel x /^.*$/={x}ませ={w}/ 
delete z

```

### 複数の形態素からなるモーダル・接続表現
#### Step 1
Tsurgeonの`createSubtree`コマンドは，
        5つ以上のノードを一度に処理できない様子なので，
        `CND`タグを削除した上で，始めの４つをまとめた後、
        残りを付け加える．

#### Step 2（以下は各表現に共通の処理）
各パーツについて、元の品詞ラベルの削除．

#### Step 3
各パーツを融合していく．

```tsurgeon
NEG=a $. (P=b $. (CND=c $. (VB3=d $. NEG3=e)))

delete c
createSubtree MD=f a d
move e >-1 f


NEG=a $. (P=b $. (CND=c $. (P=d $. (VB3=e $. NEG3=f))))

delete c
createSubtree MD=g a d
move e >-1 g
move f >-1 g

NEG=a $. (P=b $. (CND=c $. (VB3=d $. (AX3=e $. NEG3=f))))

delete c
createSubtree MD=g a d
move e >-1 g
move f >-1 g

% 「ようになる」と使役の「ようにする」
PP=pp < (P=b < に) $. (__=star < *に* $. (VB=c < /^(な[ら-ろっ])|(せ|さ|し|する|すれ|しろ|せよ)$/)) < (NP=np < (IP-EMB=emb $. (N=a < よう)))

delete star
excise pp pp
excise np np
excise emb emb
createSubtree MD a c


% 「ないと駄目」「なくちゃ駄目」
NEG=a $. (P=b $. (CND=c $. ADJN3=d))

delete c
createSubtree MD a d

%「ていい」「て結構」「て構わない」
P=a $. (CND=b $. ADJI3|ADJN3|VB3=c)

delete b
createSubtree MD a c


%「てもいい」「ては駄目」
P=a $. (CND=b $. (P=c $. ADJI3|ADJN3=d))

delete b
createSubtree MD a d


%「ても構わない」「ても差し支えない」
P=a $. (CND=b $. (P=c $. (VB3=d $. NEG3=e))) !$, NEG

delete b
createSubtree MD=f a e


%「ても構いません」
P=a $. (CND=b $. (P=c $. (VB3=d $. (AX=e $. NEG3=f)))) 

delete b
createSubtree MD=f a f



!ADJI3=y < /^[い良よ](かろ|かっ|く|う|い|けれ)$/ $, (CND=cnd $, (IP-ADV=adv <-1 P=p))

excise adv adv
delete cnd
createSubtree MD p y


!ADJI3=y < /^[い良よ](かろ|かっ|く|う|い|けれ)$/ $, (CND=cnd $, (PP=pp <-1 (P=p < たら|と $, IP-ADV=adv)))

excise pp pp
excise adv adv
delete cnd
createSubtree MD p y


%「だけでよい」
PP=pp < IP-ADV=adv < (P < だけ $. (P < で)) $. (__=adj < /^[よ良い]/)

excise pp pp
excise adv adv
relabel adj /^.*$/MD/


%「ほうが良い」
PP=x  $. ((__=y < *が*) $. (ADJI=c < /^良|よ|好|宜|(いい$)/)) <-1 (P=b < が $, (NP=z < IP-EMB=w < (N=a < ほう|方) ))

excise x x
delete y
excise z z
excise w w
createSubtree MD a c

%「にきまっている」
PP=pp <-1 (P=a < に) $. (VB=b < きまっ|決まっ $. (P=c < て $. (VB2=d < いる))) < IP-NML=nml

excise pp pp
excise nml nml
createSubtree MD a d

%「にすぎない」
PP=pp <-1 (P=a < に) $. (__ < すぎ|過ぎ=b $. NEG=c) < /^IP/=sister 

excise pp pp
excise sister sister
createSubtree MD a c

PP=pp <-1 (P=a < に) $. (__ < すぎ|過ぎ=b $. NEG=c) < /^NP/=sister 

excise pp pp
relabel sister NP-PRD
createSubtree MD a c


%「とは限らない」
__=c < 限ら|かぎら $. NEG=d $, (NP-SBJ=sbj < *と* $, (PP=pp <1 IP-NML=nml <-2 (P=a < と) <-1 (P=b < は)))

delete sbj
excise pp pp
excise nml nml
createSubtree MD a d


__=c < 限ら|かぎら $. NEG=d $, (PP=pp <1 NP=np <-2 (P=a < と) <-1 (P=b < は))

relabel np NP-PRD
excise pp pp
createSubtree MD a d

__=c < 限ら|かぎら $. NEG=d $, (PP=pp <-1 (P < は) <-2 (CP-THT=cp < IP-SUB=sub < (P=a < と)))

excise pp pp
excise cp cp
excise sub sub
createSubtree MD a d

%と同時に
PP=pp < (P=a < と) $. (N=b < 同時 > (NP=np $. (P=c <に))) 

excise np np
excise pp pp
createSubtree P-CMPLX a c

%より(ほか)ない
N=n < ほか|他 $, IP-EMB=emb > (NP-SBJ2=sbj2 $. (ADJI=adj < /^な|無/))

excise emb emb
excise sbj2 sbj2
createSubtree MD n adj

N=n < ほか|他 $, (PP=pp <1 IP-NML=nml <2 P=p) > (NP-SBJ2=sbj2 $. (ADJI=adj < /^な|無/))

excise nml nml
excise sbj2 sbj2
excise pp pp
createSubtree MD p adj


%IPのサブカテゴリー調整
IP-NML=nml $ P-CMPLX

relabel nml IP-ADV


%NP-TMP,NP-ADVを投射するNの接続詞化
/^NP-(TMP|ADV)$/=np < (/^IP-EMB/=ip $. N=n)

relabel np PP-SCON
relabel ip IP-ADV
relabel n P

%IP-EMBと助詞を伴うNの接続詞化
PP=pp < (NP=np < IP-EMB=ip < ((N=a (< /^(とき|時$|瞬間|際|間$|あいだ|前$|まえ|後$|あと|度$|たび|内$|うち$)/ | < まま|限り|かぎり|よう|とおり|通り|ほか|ため|為|為め|ほど|程|ところ|所|場合|間|以上|如く|あまり|余り|中|なか|うち|内|上|うえ|ゆえ|とたん|途端|途中|次第|あげく|挙句|末|結果|際|反面|半面|一方|さい))) $. (P=b <に|も|は !. (!/^NP-(TMP|ADV)/ < /^((\*.+\*)|\*)$/)))

excise np np
relabel ip IP-ADV
createSubtree P-CMPLX a b
relabel pp PP

%「Nには」「Nにも」への一語化（保留）
P-CMPLX=cmplx <-1 (P < に) $. (P=p < は|も)

move p >-1 cmplx


%一語化する処理
MD|P-CMPLX < (__=x < __)

excise x x


__=x $ __=y !< __

relabel x /^.*$/={x}={y}/
delete y


P-CMPLX=x

relabel x P

```

例：
```
(NEG なけれ)(P ば)(CND *)(VB3 なら)(NEG3 ない)
-> (MD なければならない)

(NEG なく)(P て)(CND *)(P は)(VB3 なら)(NEG3 ない)
-> (MD なくてはならない)

(predicate)(P て)(CND *)(P は)(VB3 いけ)(NEG3 ない)
-> (predicate)(MD てはいけない)
```

#### Step 4
処理の過程でIP-ADVが破壊されflatな構造が生じた結果，主語が二重になることがある．
そのような状態は解消しなければならないが，
その際まずよりspecificな主語を残し，次により前の主語を残すという処理を追加する．

```tsurgeon
/SBJ$/ < /^\*[ぁ-ん]+\*$/ $ (/SBJ$/=x < /^\*[a-z+]+\*$/)

delete x


/SBJ$/ < /^\*(speaker|hearer)/ $ (/SBJ$/=x < /^\*(exp|pro)\*/)

delete x


/SBJ$/ < *pro* $ (/SBJ$/=x < *exp*)

delete x


/SBJ$/  $.. (/SBJ$/=x < /^\*[a-z+]+\*$/)

delete x

```


#### 「だろう」「でしょう」
かつてのKeyakiであった、コピュラ+「う」という分析は現状のNPCMJでは採られておらず，
全て一語「だろう」「でしょう」と扱われているので，それに準じる．
```
(AX だろ)(MD う) => (MD だろう)
```

```tsurgeon
AX=a < だろ|でしょ=b $. (MD=c < う)

move b >1 c
delete a

__=x $ __=y !< __

relabel x /^.*$/={x}={y}/
delete y

```

### 「つもり」
Keyakiでは，NPを投射するが，この投射は，簡潔な変換のために，外しておいて，述語文の文末表現にしておきたい．
しかし，一方で，「つもりはみじんも無かった」という例においては，「つもり」は
あくまでもNPであり，変形をすべきではない．

従って，本スクリプトでは変形は行わず，変形は手動で行うことにした．

```tsurgeon
%__=np
%  <-2 __=ipemb
%  <-1 (
%    N=z 
%      < つもり
%      )
%
%relabel z MD-EMB
%excise np np
%excise ipemb ipemb
%
%
%__=i < MD-EMB=x !< /SBJ/
%
%insert (PP-SBJ *pro*) >1 i
%relabel x MD

```

## NUMCLPの正規化
### 量化的でないNUMCLPの処理
NPとラベルを張り替える．
年月日，序数詞，元号年，学年などを除外している．

```tsurgeon
CL < 年|日|分|秒 > (NUMCLP=x $ (NUMCLP|NP < (CL < 年|月|日|時|分|秒)))

relabel x NP


年 > (CL > NUMCLP=x)  (, /^[1-9]{3,4}/ | > (CL > (NPR $. NUMCLP)))

relabel x NP


/^.+日$/  > (NUM !$. CL > NUMCLP=x)

relabel x NP


CL (< 歳|才|月|時|階|部|年生|年度|年代 |< /^[^項]+目$/)  > NUMCLP=x

relabel x NP


NUM < /^第./ > NUMCLP=x

relabel x NP


__ (== NPR | == (N < /[校学小中高大]$/)). (NUMCLP=x < (NUM.年))

relabel x NP

```
### headless NUMCLPの処理
CLがなければ，NUMCLPはheadlessである．

```tsurgeon
NUMCLP=numclp !< CL
  !== /#deriv=/

relabel numclp /^.*$/={numclp}#deriv=unary-CL/

```


## NPの正規化
### 前提
Keyakiにおいて、投射されていないN（あるいはQ、あるいはそれに類するもの）があってはならない。
ある場合、それはアノテーションミスなので、予め直しておくこと。

### 名詞句内部の数量詞句
名詞句内部の数量詞句は，`PP;*`や`NP;*`や`PRN;*`とアノテートされている．\
この`;*`は，後ほど，数量詞の解釈位置を決める際に使われる．\
ここでは，後の処理のために，素性`#qinner=true`に変換しておく．\
特に，「(NP (NML 烏丸線、近鉄線)(PRN (NP;* 双方)))」のような名詞句内に量化的な句が後置される場合には，\
処理の都合上`PRN`の側に素性を移しておく．\
この素性は，後で削除される．\
なお`NP;*`分析のうち，`PRN`に支配され`NUMCLP`を単独支配するケース(`(N ...)(PRN (NP;* (NUMCLP ...)))`)については別の扱いをする．\
そのほとんどは`NUMCLPのN`と言い換えが可能であり，\
デフォルトでは`Q`や`QN`の扱い(`(NP (N ...)(NUMCLP ...))`)に準じるほうが良いと考えられるため，\
ここで`PRN`と`NP;*`を削除する処理をしておく．\
ただし，`NUMCLP`であっても`PRN`を投射したほうがいいケースは少数ながらあり（例：`長男一人`,`宮城、岩手、福島、栃木4県`），手動で直すことにする．

```tsurgeon
PRN=x < (NP;*=y <: /^NUMCLP(#deriv=unary-CL)?$/)

excise x x
excise y y


NP;*=x > PRN=y !< NUMCLP

relabel x /^.*$/NP/
relabel y /^.*$/PRN#qinner=true/


/^(.*)\;\*$/#1\%cat=x
  !> ID

relabel x /^.*$/\%{cat}#qinner=true/

```


### 統語情報の組み入れ
Keyakiでは、格助詞のあるNP（それらはPPに支配されている）と、
        その文法役割は、別々のノードで表現されている。
これらを統合したい。

```tsurgeon
/^PP/=x $. (
    /^NP-(.*)$/#1\%role=y 
        < (
            /^(\*.*\*|\*)$/
            !== /pro|arb|exp|speaker|hearer/
        )
)

relabel x /^.*$/={x}-\%{role}/
delete y

```

例：
```
(PP ... (P ...)) (NP-SBJ *)
-> (PP-SBJ ... (P ...))
```

次に、格助詞のないNP（これは裸のNPになる）についても、
        助詞のあるNPと揃えるため、空の助詞をかぶせてPPとする。
音型のないNP（空代名詞類）に対してもこの操作が適用されるが、次で取り消される。
さらに、「AもBも」のような等位接続の構造について、
conjunctsにdependencyを振らない、という処理を維持するため、
#deriv=conjという素性に関してはNPが保持するようにする。

```tsurgeon
/^NP-([^#]+)/#1\%role=x 
    !> /#deriv=unary-case/

relabel x NP
adjoinF (=z @) x
relabel z /^.*$/PP-\%{role}#deriv=unary-case/

```

例：
```
(NP-SBJ ... (N ...))
 -> (PP-SBJ#deriv=unary-case (NP ... (N ...)))
```

空のNP（空代名詞など）については、
        前の変換で挿入された空の助詞を削除する。

```tsurgeon
/^(PP.*)#deriv=unary-case(.*)/#1\%pre#2\%post=pp
  < (NP=z < /^\*/) 

relabel pp /^.*$/\%{pre}\%{post}/
excise z z

```

例：
```
(PP-SBJ#deriv=unary-case (NP *pro*))
    -> (PP-SBJ *pro*)
```

注意：これより先、NPには文法役割はつかず、すべてPPにつくことになる。

### 呼格名詞句の処理
Keyakiに`(CLEAN *VOC*)`という後処理用の？タグが残っているので、それを削除する。

```tsurgeon
CLEAN=x < __

delete x

```

### 量化詞類の処置
Qなどの投射をNPqにする．
量化的なDの投射，indeterminate wh-pronoun + も/かについても同様に扱う．

```tsurgeon
/^(Q|QN|NUMCLP|WNUM)(.*)$/ > (/^(NP|NML)(.*)$/#2\%nprem=y !== /NPq/)

relabel y /^.*$/NPq\%{nprem}/


D (< あらゆる|ありとあらゆる|ある|さらなる|とある|或る|或|或（ある） |< (さる !. こと)) > (/^(NP|NML)(.*)$/#2\%nprem=y !== /NPq/)

relabel y /^.*$/NPq\%{nprem}/



/^(NP|NML)(.*)$/#2\%nprem=y < WPRO < (P < も) !== /NPq/

relabel y /^.*$/NPq\%{nprem}/


/^(NP|NML)(.*)$/#2\%nprem=y   < WPRO > (/PP/ < (P < も|でも)) !== /NPq/

relabel y /^.*$/NPq\%{nprem}/


/^(NP|NML)(.*)$/#2\%nprem=y  << WD < (P < も) !== /NPq/

relabel y /^.*$/NPq\%{nprem}/


/^(NP|NML)(.*)$/#2\%nprem=y << WD > (/PP/ < (P < も|でも)) !== /NPq/

relabel y /^.*$/NPq\%{nprem}/


/^(NP|NML)(.*)$/#2\%nprem=y < WPRO|WD < (P < か) !== /NPq/

relabel y /^.*$/NPq\%{nprem}/


/^(NP|NML)(.*)$/#2\%nprem=y < WPRO|WD > (/PP/ < (P < か) <! CONJP) !== /NPq/

relabel y /^.*$/NPq\%{nprem}/


```

例：
```
(NP (WNUM ...))
-> 
(NPq (WNUM ...))
```

### 指示詞類の処置
指示詞類`(W)PRO`，`(W)D`，`NPR`（以下「指示詞類」と呼ぶ）が，NPに含まれているとき，
  その指示詞類は，主要部と見なす．
このために，まず，*最右*の指示詞より右側を，改めて`NP`の下にまとめる．
次に，投射`NP(q)`を`NP(q)d`に改める．

#### 指示詞類の右に1つのノードしかない場合
```tsurgeon
%/^(NP|NPq)(.*)$/#1\%npcat#2\%nprem=np 
%  < (/^(D|WD|PRO|WPRO|NPR)$/
%      !$, /^(D|WD|PRO|WPRO|NPR)$/ 
%      $. (
%        /^(N|Q|QN|CL|IP-NML|NP|NUMCLP|NML)$/=only
%          !$. __
%      )
%  )
%
%createSubtree (=new ) only
%relabel new /^.*$/__cat_\%{npcat}/
%relabel np /^.*$/\%{npcat}d\%{nprem}/
%
%/__cat_(NP|NPq)/#1\%cat=p
%
%relabel p /^.*$/\%{cat}/

```

#### 2つ以上の場合
```tsurgeon
%/^(NP|NPq)(.*)$/#1\%npcat#2\%nprem=np 
%  < (/^(D|WD|PRO|WPRO|NPR)$/
%      !$, /^(D|WD|PRO|WPRO|NPR)$/ 
%      $. (__=dr
%              $.. (__=last !$. __)))
%
%createSubtree =new dr last
%relabel new /^.*$/={np}/
%relabel np /^.*$/\%{npcat}d\%{nprem}/

```

例：
```
(NP (D この) (N しぐさ))
-> (NPd (D この) (NP (N しぐさ)))

(NP (D この) (PRO ぼく))
-> (NPd (D この) (NP (PRO ぼく)))

(NP (D こいつ))
-> (NPd (D こいつ))

(NP (IP-REL 美しい) (D この) (N 星))
-> (NPd (IP-REL 美しい) (D この) (NP (N 星)))

(NP (D この) (PRO 私))
-> (NPd (D この) (PRO 私))
```

（2019.12.11追記）現状では固有名`NPR`も指示詞の類として扱っている．
これは`明治20年``ホームズ自身`のような表現のアノテーションに合わせたものと考えられるが，
`「親沼公園」`のように括弧でくくられたケースに関して不具合を引き起こすので，
アドホックに例外指定を入れた．いずれはNPの構造について真剣に考えなければならない．

（2020.6）指示詞類のないNPについては，空主要部によるNPd投射を設けないこととした．
等位接続との予期しない相互作用を回避するためである．

(2020.11.2) ccg2lambdaのために，一度この特性を無効にした．

### 量化詞の添字付け
量化詞に添え字を振っていく．
ただし，技術的な理由により，1文には高々9つまで量化的な表現しかないと仮定する．
（multi-sentenceがたくさんある場合，このような取り扱いが破綻する可能性はある）

量化詞であるものをKeyakiで確認するためのクエリ：
```
/^Q|NUMCLP/ !< (CL < 年|月|日|才|歳|時|階) .. (/^Q|NUMCLP/ !< (CL < 年|月|日|才|歳|時|階) .. /^Q|NUMCLP/ !< (CL < 年|月|日|才|歳|時|階) .. (/^Q|NUMCLP/ !< (CL < 年|月|日|才|歳|時|階) .. (/^Q|NUMCLP/ !< (CL < 年|月|日|才|歳|時|階) .. (/^Q|NUMCLP/ !< (CL < 年|月|日|才|歳|時|階)))))

```

量化的でないNUMCLPについては，pretreatmentsでNPにラベルを張り替えてあるので，
この操作の対象にならない．

```tsurgeon
/^NPd?q/=x 
  !== /index/ 
  !,, /index/ 
  !.. /index/ 
  !>> /index/
  !,, /^NPd?q/ 
  !< /^NPd?q/ 

relabel x /^(.*)$/$1#index=1/

/^NPd?q/=x 
  !== /index/ 
  (,, /index=1/ | .. /index=1/) 
  !,, /index=2/ 
  !.. /index=2/ 
  !>> /index=2/ 
  !< /^NPd?q/

relabel x /^(.*)$/$1#index=2/

/^NPd?q/=x 
  !== /index/ 
  (,, /index=2/ | .. /index=2/) 
  !,, /index=3/ 
  !.. /index=3/ 
  !>> /index=3/
  !< /^NPd?q/

relabel x /^(.*)$/$1#index=3/


/^NPd?q/=x 
  !== /index/ 
  (,, /index=3/ | .. /index=3/) 
  !,, /index=4/ 
  !.. /index=4/ 
  !>> /index=4/ 
  !< /^NPd?q/

relabel x /^(.*)$/$1#index=4/

/^NPd?q/=x 
  !== /index/ 
  (,, /index=4/ | .. /index=4/) 
  !,, /index=5/ 
  !.. /index=5/ 
  !>> /index=5/ 
  !< /^NPd?q/

relabel x /^(.*)$/$1#index=5/

/^NPd?q/=x 
  !== /index/ 
  (,, /index=5/ | .. /index=5/) 
  !,, /index=6/ 
  !.. /index=6/ 
  !>> /index=6/ 
  !< /^NPd?q/

relabel x /^(.*)$/$1#index=6/

/^NPd?q/=x 
  !== /index/ 
  (,, /index=6/ | .. /index=6/) 
  !,, /index=7/ 
  !.. /index=7/ 
  !>> /index=7/ 
  !< /^NPd?q/

relabel x /^(.*)$/$1#index=7/


/^NPd?q/=x 
  !== /index/ 
  (,, /index=7/ | .. /index=7/) 
  !,, /index=8/ 
  !.. /index=8/ 
  !>> /index=8/ 
  !< /^NPd?q/

relabel x /^(.*)$/$1#index=8/

/^NPd?q/=x 
  !== /index/ 
  (,, /index=8/ | .. /index=8/) 
  !,, /index=9/ 
  !.. /index=9/ 
  !>> /index=9/ 
  !< /^NPd?q/

relabel x /^(.*)$/$1#index=9/

```

### NMLの廃止
`NP`内において、`NML`という中間投射があるが、これを`NP`に同一化する。
```tsurgeon
/^NML/=x 

relabel x /^NML(.*)$/NP$1/

```

### `NP <: PP`の廃止
```
(NP (PP (IP-ADV 殴ってしまいたい) 
        (P ほど)))
```
というように，PPがゼロ派生でNPをunaryに投射する場合がある．
ここでは，そのようなものについては`IP-EMB N`に引き戻すこととする．

```tsurgeon
/^PP/=red
  >: /^NP/
  < /^IP-ADV/=ip
  < /^P/=p
  
excise red red
relabel ip IP-EMB
relabel p N

```

### `NP-PRD <: IP-EMB`
```
(NP-PRD (IP-EMB たまには休みたい，)) みたい な
```
という例に関しては，unary branchを補ってあげる．

```tsurgeon
/^NP/=np
  <: /IP-EMB/ 
  !== /#deriv=/

relabel np /^.*$/={np}#deriv=unary-IPEMB-headless/

```

この段階で、名詞類の最大投射は`NP(q?d?)`に限られる。
中間投射はみな`NP`である．

### 意味論のための追加の枝
現状の名詞句の句構造は，次の通りである：
```
NP -> ... (NP | N) ...
```
しかし，ccg2lambdaの量化子についての（暫定的な）解釈のために，NP-Nの枝を，unary branchingとして予約したい．
そうすると，句構造は次のようになる：
```
NP -> *N_1 [unary]
*N_1 -> ... NP ...
*N_1 -> ... (*N_2 | Q | D | PRO) ...
```
このうち，`*N_1`はunary branchingのものであり，`*N_2`は，もともとの名詞である．
`*N_2`と`*N_1`とが混同されないようにしたい．

事実としては，`*N_2`のほとんどは，主要部であるので，relabelのあと，`$\*N_1`という範疇になり，消える．
しかし，一部の`*N_2`については，（低いスコープでの連体修飾のために）relabelの後に残ることがある．
従って，やはり，`*N_2`を，名前を変更することで，`*N_1`と区別しておきたい．

`*N_2`のもの（現時点では`N`）全てについて，この段階で`Ns`と名付けることにする，
当然，前述のように，全ての`Ns`（=`*N_2`）が，relabelの後に生き残るわけではないが，*生き残るものは生き残る*．

```tsurgeon
/^N$/=n

relabel n Ns

```

ここで，`N`という範疇はなくなっている．

その後，全てのNPに，`*N_1`として，`Nq?`を改めて導入する：
```tsurgeon
/^NP(?<!q)/=np
  !== /#deriv=/

adjoinH ( N@) np
relabel np /^.*$/={np}#deriv=unary-NP-type-raising/

/^NPq/=np
  !== /#deriv=/

adjoinH ( Nq@) np
relabel np /^.*$/={np}#deriv=unary-NP-type-raising/

```

（注）なお，以前では，
```
(DP (NP (N)))
```
のような3段構造を採っていたこともあるが，「日本語CCGツリーバンク」に合わせるために，これを放棄した．

### 期待される生成規則
```
PP-%{role}                     -> NP(q?)#deriv=unary-NP-type-raising P
PP-%{role}#deriv=unary-case    -> NP(q?)#deriv=unary-NP-type-raising

NP(q?)#deriv=unary-NP-type-raising -> N(q?)

N(q?) -> ... ( NP(q?)#deriv=... | Ns | D | Q | QN | NUMCLP | WNUM | NPR | PRO ) ...
```

## 副助詞のCP-THT下への繰り入れ

```tsurgeon
PP=a < (/^CP-THT/=b $. P=c) !$ N

excise a a
move c >-1 b

```

例：
```
  (PP (CP-THT ...(P と)) (P は))
  -> (CP-THT ...(P と) (P は))
```

## とりたて助詞＋格助詞を含むPPの処理
名詞ととりたて助詞をまず1つの構成素NPとし，その後格助詞とともにPPを投射させる．
この際，とりたて助詞は名詞に対するadjunct，格助詞は中間のNPをcomplementとするheadとする．
これは最終的にとりたて助詞に`NP\NP,` 格助詞に`NP\PP`というカテゴリを振ることを目的とする処理である．

```tsurgeon
/^PP.*$/=pp
  <1 __=fst 
  < (/^NP/=np 
     !< /role/
     $. (/^P$/=optr 
        !< role
         < は|も|さえ|でも|すら|まで|だけ|ばかり|のみ|しか|こそ|など|なんか|なんて|くらい
         $. (/^P/=role  < を|に|の|へ|が|と|から|で|より|まで)
        )
    )

createSubtree NP=intm fst optr
relabel np /^.*$/={np}#role=h/
relabel optr /^.*$/={optr}#role=a/
relabel intm /^.*$/NP#role=c/

```

## IPの正規化 1：埋め込み節と主節との接続
### IP-ADVの正規化 1：助詞の繰り上げや補充
副詞従属節を導く助詞は、そのうちのいくつかはIP-ADVの中にあり、また、いくつかは外にある。
これは語の従属度の度合いを反映したものである（詳しくはKeyakiのマニュアルを見よ）．

内側に入り込んでいるPは、繰り上げられる。

```tsurgeon
/^IP-ADV/=ip 
        <-1 P 
        <1 __=x 
        <-2 __=y 
        !>3 __

createSubtree IP-ADV x y
relabel ip PP

```

IP-ADVの直後に、意味表示を考える上でPと見なしたほうが都合の良いCONJが現れることがある。
この場合、CONJをPに貼り替え、IP-ADVを補部に取るPPを投射させる。

```tsurgeon
/^IP-ADV/=ip
        !<-1 P
        $. (CONJ=conj < 一方で|だけじゃなくて|だけでなく|だけではなく|だけではなくて|って言うか|っていうか|ではなく|とか|どころか|とともに|のではなく|ばかりか|ばかりでなく|プラス)

createSubtree PP ip conj
relabel conj P

```

内側にも外側にもP（に相当するもの）がないようなIP-ADV（動詞の連用形で直接接続されているような場合であろう）については、
空のPを一つ挟ませる。

```tsurgeon
/^IP-ADV/=ip 
    >! /^PP/ 
    >! /#deriv=/

adjoinF (=pp @) ip
relabel pp /^.*$/PP#deriv=unary-IPADV/

```

例：
```
(IP (IP-ADV ...) ...)
-> (IP (PP#deriv=unary-IPADV (IP-ADV ...)))
```


### IP-RELの正規化
IP-RELには、もれなく空のPを付け加えることにする。

```tsurgeon
/IP-REL/=ip !> /#deriv=/

adjoinF (=pp @) ip
relabel pp /^.*$/PP-REL#deriv=unary-IPREL/

```


### IP-RELの正規化：深いトレースの処理
トレースが深く埋め込まれている関係節の処理を行う。

#### IP-SMC下に埋め込まれているケース
```tsurgeon
/^IP-REL/=z !< (__ <: *T*) < (!/^PP/ << (/^PP-./=y < *T*=x !> /^IP-REL/))

relabel x *trace*
adjoinF (=w @) z
adjoinF (=v @) w 
insert (TRACE=u *T*) $+ w
relabel u /^.*$/={y}/
relabel w /^.*$/VBS#role=h/
relabel v /^.*$/IP-REL#role=c/

```
#### その他のケース(IP-ADVなど)

```tsurgeon
/^IP-REL/=z !< (__ <: *T*) < (/^PP/ << (/^PP-./=y < *T*=x !> /^IP-REL/) !>> /^IP-EMB/)

relabel x *trace*
adjoinF (=w @) z
adjoinF (=v @) w 
insert (TRACE=u *T*) $+ w
relabel u /^.*$/={y}/
relabel w /^.*$/VBS#role=h/
relabel v /^.*$/IP-REL#role=c/

```

### IP-ADVの正規化 2：統語情報の組み入れ
IP-ADV（連用節）には、主節と3種類の関係を結ぶことがある：CND、SCON、CONJ。
これらの統語情報は，例えば，以下のように，IP-ADVの右隣で，`(CONJ *)`のように，（多くの場合）空範疇によって標示される．
```
(IP-MAT (PP (IP-ADV 太郎は遊ん) で)
        (CONJ *)
        (PP-SBJ 花子は)
        (VB 勉強)
        (VB0 し)
        (AXD た))
```
これらの統語情報を（格情報を`PP < NPd`に組み入れたのと同様に）
PPに組み入れることをしたい．

ただし，前処理が必要である．`CONJ`に限っては，
空範疇ではなく，音型を持つ語彙によって`IP-ADV`に標示を
与えることがあるからである．
空範疇`(CONJ *)`を挿入することで，
空範疇による標示の場合に帰着することにする．

```tsurgeon
/^PP/=clause
  < /^IP-ADV/
  $. (
    /^CONJ$/ <! /\*/
  )

insert (CONJ *) $- clause

/^PP/=clause
  < /^IP-ADV/
  $. (
    PU $. (/^CONJ$/ <! /\*/)
  )

insert (CONJ *) $- clause

```

例：
```
(IP-MAT (PP (IP-ADV 太郎は遊ん) で)
        (CONJ そして)
        (PP-SBJ 花子は)
        (VB 勉強)
        (VB0 し)
        (AXD た))
-> 
(IP-MAT (PP (IP-ADV 太郎は遊ん) で)
        (CONJ *)
        (CONJ そして)
        (PP-SBJ 花子は)
        (VB 勉強)
        (VB0 し)
        (AXD た))
```

ここで，本来の処理をやっと行うことができる．
`IP-ADV`は、前節での変換により、
すべて`PP`の下に入っていることに注意。

```tsurgeon
/^(PP.*?)(#?.*)$/#1\%cat#2\%rem=x $. (/^(CONJ|SCON|CND)$/=y < /^\*$/)

relabel x /^.*$/\%{cat}-={y}\%{rem}/
delete y

```


例：
```
(IP-MAT (PP (IP-ADV 太郎は遊ん) 
            (P で))
        (CONJ *)
        ...)
-> 
(IP-MAT (PP-CONJ (IP-ADV 太郎は遊ん) 
                 (P で))
        ...)
```

関係が標示されていないものについては、デフォルトでSCONを与える。
```tsurgeon
/^PP$/=x < /IP-ADV/

relabel x /^.*$/={x}-SCON/

```

例：
```
(PP (IP-ADV ...) (P ...))
   -> (PP-SCON (IP-ADV ...) (P ...))
```


### 期待される生成規則
```
PP-%{role} -> (IP-ADV | IP-EMB) P
```

## IPの正規化 2：項構造の決定
IPの項構造を決定する．
特に，以下の2つが問題になる．

1. 欠けている項の補充
  - `<!--  -->*PRO*`
  - `*pro*`：これが欠けているのは，Keyakiのアノテーションの誤りである．
     こちらで補うのはかえって問題を大きくすることがあるので，IP-SUB, IP-MAT, IP-RELを除いてはしない．
2. 項構造を変えるアイテム（受動，使役）の標示
3. 項構造を変えるアイテムが節を投射するようにし，そこでさらに`*PRO*`を挿入する．

以下，これを順番にやっていく．

### コントロール`IP-ADV`
コントロールが生じるのは，`PP-SCON|PP-CND|PP-PRD|PP-ADV < IP`となるIPであって，
`PP-SBJ`が欠けている場合である．
`PP-SBJ`は，主節の何かしらの項に束縛される`*PRO*`である．
具体的にどの項になるのかについては，Keyakiのシステムでは取り決めがあるが，
ここでは関心があるわけではない．

```tsurgeon
/^IP-ADV/=i
  > /^PP(-(SCON|CND|PRD|ADV)|.+unary-IPADV)/
  !< /-SBJ(#.+)?$/
  !< /ICH/

insert (PP-SBJ *PRO*) >1 i

```

### コントロール`IP-SMC`
また，`IP-SMC`, `IP-NML`に関しても同様である．
```tsurgeon
/IP-(SMC|NML)/=i !< /-SBJ(#.+)?$/ !< /ICH/

insert (PP-SBJ *PRO*) >1 i

```
`PP-SBJ2`ではなく，`/PP-SBJ$/`の有無が重要であることに注意．

### コントロール`IP-EMB`
`IP-EMB`（名詞の取る補文節）も，Keyakiにおいてコントロールを呼び起こすことがある．
しかし，sentence radical自体が問題になることがない（全体として）ので，
`*PRO*`の代わりに`*pro*`を用いる．

```tsurgeon
/IP-EMB/=i !< /-SBJ(#.+)?$/ !< /ICH/

insert (PP-SBJ *pro*) >1 i

```

### ATB `IP-ADV`
今度はまず，先行詞のある主節側から見ていく．
主節から項を「降ろす」先の埋め込み節は，`PP-CONJ < IP-ADV`という配置をしている．
そこで，欠けている項が`IP-ADV`にあるのであれば，それを`*PRO*`で補う．

埋め込み節においても，項の文法役割に関するヒエラルキーを保ちたい．
従って，文法役割のヒエラルキーの順に補充を行う．

```tsurgeon
/^IP/=matrix
  < ( /SBJ/
        !== /SBJ2/
        $.. (
          /^PP-CONJ/
                < (
                  /^IP-ADV/=emb
                        !< (
                            /^(CP-THT|PP)-(SBJ)/
                            !== /SBJ2/
                        )
                        !< /ICH/
                )
        )
  )

insert (PP-SBJ *PRO*) >1 emb

```

以下は，主語を欠いた`PP-CONJ`が，自身を埋め込む節の主語に先行する場合に対応する．
主語を補うという点に関してはやっていることは同じだが，これはATBの対象にならないという点で理念上は上記とは異なる．
NPCMJ的にも主語は必要なはずであるため，`*pro*`を補う．

```tsurgeon
/^IP/=matrix
  < ( /SBJ/
        !== /SBJ2/
        $,, (
          /^PP-CONJ/
                < (
                  /^IP-ADV/=emb
                        !< (
                            /^(CP-THT|CP-QUE|PP)-(SBJ)/
                            !== /SBJ2/
                        )
                        !< /ICH/
                )
        )
  )

insert (PP-SBJ *pro*) >1 emb

```

`PP-SBJ2`は必ずしもいつも補充が必要，というわけではない．
埋め込み節に`PP-SBJ`があり，しかもそれが実質的（すなわち，`*PRO*`以外のもの）である
場合，補充は不要である．

```tsurgeon
/^IP/=matrix
  < ( /^PP-(SBJ2)/#1\%arg
        $.. (
          /^PP-CONJ/
                < (
                  /^IP-ADV/=emb
                        !< /^PP-(SBJ2)/#1\%arg
                        !< (/^PP-SBJ/ !< /\*PRO\*/)
                        !< /ICH/
                )
        )
  )

insert (PP-SBJ2 *PRO*) >1 emb

```

その他の項について，`*PRO*`を補充する位置に気を付けながら：
```tsurgeon
/^IP/=matrix
  < ( /^PP-(LGS)/#1\%arg
        $.. (
          /^PP-CONJ/
                < (
                  /^IP-ADV/=emb
                        !< /^PP-(LGS)/#1\%arg
                        < (/^PP-SBJ/=embsbj !$.. /SBJ/)
                        !< /ICH/
                )
        )
  )

insert (PP-LGS *PRO*) $- embsbj

/^IP/=matrix
  < ( /^PP-(OB1)/#1\%arg
        $.. (
          /^PP-CONJ/
                < (
                  /^IP-ADV/=emb
                        !< /^PP-(OB1)/#1\%arg
                        < (/^PP-(SBJ|LGS)/=embsbj !$.. /SBJ|LGS/)
                        !< /ICH/
                )
        )
  )

insert (PP-OB1 *PRO*) $- embsbj

/^IP/=matrix
  < ( /^PP-(OB2)/#1\%arg
        $.. (
          /^PP-CONJ/
                < (
                  /^IP-ADV/=emb
                        !< /^PP-(OB2)/#1\%arg
                        < (/^PP-(SBJ2?|LGS|OB1)/=embob1 !$.. /SBJ2?|LGS|OB1/)
                        !< /ICH/
                )
        )
  )

insert (PP-OB2 *PRO*) $- embob1

```

### 欠けた主語の挿入
Keyakiのアノテーションミスにより、主語を欠いたIP-MAT, IP-SUB, IP-RELに`*pro*`を挿入する。

```tsurgeon
/^IP-(MAT|SUB)$/=i !< /-SBJ(#.+)?$/

insert (PP-SBJ *pro*) >1 i

IP-REL=i <1 (__ << *T*) !< /-SBJ(#.+)?$/

insert (PP-SBJ *pro*) >2 i 

```

### ダミー項の削除
虚辞`*exp*`を削除する．

```tsurgeon
__=e < /^\*exp\*$/

delete e

```

### 空要素のスクランブリングの防止
`*pro*`など空要素が前に出ることにより音形のないscramblingが起きてしまうことを防ぐ。


```tsurgeon
/PP-OB/=x < /^\*.+\*$/ $.. /PP-SBJ/=y !< *T*

move x $- y

```
`*T*`については移動させない。
`*PRO*`については例外扱いしなければならないかもしれない。
OB1とOB2の語順については、述語によって扱いが違うので一律には扱わない。


これで節の項構造が決まった。

### 期待される生成規則
```
IP-%{role}

```

## IPの正規化 3：項構造を変える表現の標示
使役類と受動類の2つがある。

- 使役類とは，`VP`（主語を除いた動詞句）を取る述語のことである．
  典型的には，使役マーカーの「させる」が挙げられる．
  他に，「てもらう」などもある．
- 受動類とは，`NP\VP` （主語に加えてさらに1つの項を除いた動詞句）を取る述語のことである．
  典型的には，受動マーカーの「られる」がこれに当たる．
  他に，「しやすい」「しにくい」などもある．

まずは，これらの範疇を`CAUS`または`PASS`に統一する．

次に，これらのいずれについても、IP-SMC分析（複文分析）に帰着したい。
使役類については、IP-SMC分析が標準であるが、受動類についてはそうではないので、まずはIP-SMCを形成する。
その次に、IP-SMCの項を復元する。

### Causative-like predicates
「てもらう」などの述語を，使役マーカーだとみなす．
```tsurgeon
__=morau 
        !== /CAUS/
        < /^(((もら|貰)[わいうえおっ])|((いただ|頂)[かきくけこい]))/ 
        $, /^IP-SMC/

relabel morau CAUS

```

### Tough predicates
Tough predicatesを受動マーカーだとみなす。

そのような述語のリスト：

- やすい
- にくい
- がたい

注意：
- 上の述語に関して，tough predicateでない語彙項目が共存することはありうる．
        例：「男性社員が育児をしやすい職場」
- 「たい」には，格付与のスキーマを変えるような用法がある（例：「これが食べたい」）．
        しかし，格付与のスキーマの特殊性は，項の文法機能や項構造を必ずしも変えるわけではない
        （例：「好きだ」「できる」）．
        また，Keyaki上でも，文法格の与え方は一定である（すなわち，ガ格にもかかわらず`(NP-OB1 これが)`）．
        従って，「たい」をtough predicateとして扱うことをしないこととする．
        「たい」は，単なる主語指向表現として，`dependency.tsng`で扱われる．

近似として、
those tough-prd-candidates that don't have objects as their brothers are real ones.
```tsurgeon
__=tough 
        !== /PASS|VBP/ 
        !$ /PASS|VBP/
        !$ /(OB1|OB2)/ 
        < /^(やす|にく|がた|易|難)(く|い|かっ|けれ)$/

relabel tough PASS

```

### テアル構文
アルを受動マーカーとみなす。

```tsurgeon

__=aru 
  < /^[あ在][らりるれろっ]$/ 
  $, PASS=x 
  !== /PASS|VBP/ 
  !$,, /OB1/

relabel aru PASS
delete x

__=aru 
  < /^あ[らりるれろっ]$/ 
  , (て|で !> AX , /^VB0?$/)
  !$, FS 
  !== /PASS|VBP/ 
  !$,, /OB1/

relabel aru PASS

```
NOTE: 受動の「（ら）れる」に後続する「てある」は繰り上げ述語として別扱いする(上記規則の適用対象外とする)．

### 受動類の複文の形成
次のことをやらなければならない：

1. 述語とその（格交替が起こっていない）項の範囲を定める：述語
    - 最左の項から，
    - `PASS`のすぐ左まで．
    - 項とは，`OB1`，`OB2`，`IP-SMC`，`CP`（ただし，`CP-.*-ADV`を除く）である．
1. その範囲をでくくり，暫定的なラベルをルートにつける．
1. `PASS`を`VBP`に変更（2つの項が欠けた埋め込み文を選択する述語だとみなす）
1. `*PRO*`を挿入．
1. 暫定的なラベルを`IP-SMC`に変更．



例：
```
(IP-MAT ... (NP-OB1 ...) (VB ...) ... (PASS ...) ...)
            ^^^^^^^^^^^^^^^^^^^^^^^^^
-> (IP-MAT ...
            >(IP-SMC (NP-SBJ *PRO*)
            >        (NP-OB2 *PRO*)
            >        (NP-OB1 ...)
            >        (VB ...) 
            > ...)
            (PASS ...)
            ...)
```

#### 2項の場合で、CP-THTが主語となるとき
```tsurgeon
/^IP/
  !< /OB1|OB2/
  < (
       /^CP-THT-SBJ/
         !== /ADV/
         !$,, /^(IP-SMC|VB0?)/
         $. __=start
         $.. (/^PASS$/=pass $, __=end)
    )

createSubtree __cat_IPSMC_2_SBJ start end
relabel pass VBP

/__cat_IPSMC_2_SBJ/=smc

insert (CP-THT *PRO*) >1 smc
insert (PP-SBJ *PRO*) >1 smc
relabel smc IP-SMC

```


#### 2項の場合
```tsurgeon
/^IP/ 
  !< /OB1|OB2/
  < (
       /^(IP-SMC|CP|VB0?)/=start
         !== /ADV/
         !$,, /^(IP-SMC|VB0?)/
         $.. (/^PASS$/=pass $, __=end)
    )

createSubtree __cat_IPSMC_2 start end
relabel pass VBP

/__cat_IPSMC_2/=smc

insert (PP-OB1 *PRO*) >1 smc
insert (PP-SBJ *PRO*) >1 smc
relabel smc IP-SMC

```

#### 3項の場合で、NP-OB1がextractされている場合
```tsurgeon
/^IP/ 
    !< /OB1/ 
    < /OB2/ 
    < ( /^(IP-SMC|CP|VB0?|.*OB2)/=start
        !== /ADV/
        !$,, /^(IP-SMC|VB0?|.*OB2)/
        $.. (/^PASS$/=pass $, __=end)
      )

createSubtree __cat_IPSMC_3-1 start end
relabel pass VBP

/__cat_IPSMC_3-1/=smc  !< /SBJ/

insert (PP-OB1 *PRO*) >1 smc
insert (PP-SBJ *PRO*) >1 smc
relabel smc IP-SMC


/__cat_IPSMC_3-1/=smc  < /SBJ/

insert (PP-OB1 *PRO*) >1 smc
relabel smc IP-SMC


```

#### 3項の場合で、NP-OB2がextractされている場合
```tsurgeon
/^IP/ 
    < /OB1/ 
    !< /OB2/ 
    < ( /^(IP-SMC|CP|VB0?|.*OB1)/=start 
            !== /ADV/
            !$,, /^(IP-SMC|VB0?|.*OB1)/
            $.. (/^PASS$/=pass $, __=end)
      )

createSubtree __cat_IPSMC_3-2 start end
relabel pass VBP

/__cat_IPSMC_3-2/=smc !< /SBJ/

insert (PP-OB2 *PRO*) >1 smc
insert (PP-SBJ *PRO*) >1 smc
relabel smc IP-SMC


/__cat_IPSMC_3-2/=smc < /SBJ/

insert (PP-OB2 *PRO*) >1 smc
relabel smc IP-SMC

```

## IPの正規化 4：述語の正規化
### Headless IPの正規化
RNRなどにより、埋め込みIPにheadがない場合がある。それを復元する。
```tsurgeon
/^IP/=x
    !< /^(VB|ADJI|ADJN|AX|CAUS|VBP|.*-PRD.*)$/
    !< (ADVP [   $. (AX|MD !$,, AX) 
          | . だろう 
          | . (だろ . う)
          | . /^らし(かろ|かっ|く|い|けれ)$/
          | . /^かもしれ/
          | < ((/^W?ADV$/ < どう|そう|そっ|なるほど) !$ /^(VB|AX|ADJI|ADJN|.P-PRD|P)(#role=.)?$/)
              ])
    !< /#role/
    !< /ICH/

insert (=vh __lex_pred) >-1 x
relabel vh /^.*$/VB#role=h/

```

例：
```
  (IP-SUB NP-SBJ NP-OB1)
  -> (IP-SUB 
             NP-SBJ 
             NP-OB1 
             (VB __lex_pred))
```

NOTE: `PRD`を述語だとここでは扱っている．

句読点や記号との順番を調節しておく．
```tsurgeon
__=x < /__lex_pred/ $, SYM|PU|RRB=y

move x $+ y

```

## IPの正規化 5：量化詞の抜き出し
量化詞には，前節のところで，すでに添え字`#index=...`を振ってある．
これらの量化詞は，他に指定がなければ，
  それを直接支配する句の中でスコープを取るものだと考える．

しかし，いくつかの量化詞は，名詞句の中にあるが，
  IP節でスコープをとると考えるべきものがある．
これらの量化詞については，IP節でスコープをとる，という標示をしておく必要がある．

### NP内部の量化詞
「3人の学生が」「学生3人が」のように，NP内部に埋め込まれている量化詞がある．

具体的には，例えば，以下がある：
```
(IP-MAT (PP-SBJ (NP (PP#qinner=true (NPq#index=2 3人の))
                    (N 学生))
                (P が))
        (VB 起きた))
```
このような量化詞は，いつも，`#qinner=true`（Keyakiでは，もともと，`;*`）に支配されている．

このような量化詞を，直近のIPで解釈させることにする．
（あるいは，名詞句全体を量化詞に変えさせる，と考えることもできるが，ここではこの考え方取っていない）
具体的には，次のように，`LFQ`をIP節を置く．
```
(IP-MAT (NPq *LFQ*-2)
        (PP-SBJ (NP (PP#qinner=true (NPq#index=2 3人の))
                    (N 学生))
                (P が))
        (VB 起きた))
```
なお，`#qinner=true`が2つ以上並列されることは，Keyaki上では存在しないので，考慮しなくてよい．
`LFQ`はIPの頭に置かれる．

```tsurgeon
__=npelem
  > /^IP/=ip
  [ <+(/^(NP|NML|N)/) (
      /#qinner=true/
        < /^(NPd?q.*)#index=(1)(.*)$/#1\%npcat#2\%num#3\%rem=NPqinner
    )
  ]
  !: /\*LFQ\*-1/

insert (=lf =ich) >1 ip
relabel lf /^.*$/\%{npcat}#role=a/
relabel ich /^.*$/*LFQ*-\%{num}/

__=npelem
  > /^IP/=ip
  [ <+(/^(NP|NML|N)/) (
      /#qinner=true/
        < /^(NPd?q.*)#index=(2)(.*)$/#1\%npcat#2\%num#3\%rem=NPqinner
    )
  ]
  !: /\*LFQ\*-2/

insert (=lf =ich) >1 ip
relabel lf /^.*$/\%{npcat}#role=a/
relabel ich /^.*$/*LFQ*-\%{num}/

__=npelem
  > /^IP/=ip
  [ <+(/^(NP|NML|N)/) (
      /#qinner=true/
        < /^(NPd?q.*)#index=(3)(.*)$/#1\%npcat#2\%num#3\%rem=NPqinner
    )
  ]
  !: /\*LFQ\*-3/

insert (=lf =ich) >1 ip
relabel lf /^.*$/\%{npcat}#role=a/
relabel ich /^.*$/*LFQ*-\%{num}/

__=npelem
  > /^IP/=ip
  [ <+(/^(NP|NML|N)/) (
      /#qinner=true/
        < /^(NPd?q.*)#index=(4)(.*)$/#1\%npcat#2\%num#3\%rem=NPqinner
    )
  ]
  !: /\*LFQ\*-4/

insert (=lf =ich) >1 ip
relabel lf /^.*$/\%{npcat}#role=a/
relabel ich /^.*$/*LFQ*-\%{num}/

__=npelem
  > /^IP/=ip
  [ <+(/^(NP|NML|N)/) (
      /#qinner=true/
        < /^(NPd?q.*)#index=(5)(.*)$/#1\%npcat#2\%num#3\%rem=NPqinner
    )
  ]
  !: /\*LFQ\*-5/

insert (=lf =ich) >1 ip
relabel lf /^.*$/\%{npcat}#role=a/
relabel ich /^.*$/*LFQ*-\%{num}/

__=npelem
  > /^IP/=ip
  [ <+(/^(NP|NML|N)/) (
      /#qinner=true/
        < /^(NPd?q.*)#index=(6)(.*)$/#1\%npcat#2\%num#3\%rem=NPqinner
    )
  ]
  !: /\*LFQ\*-6/

insert (=lf =ich) >1 ip
relabel lf /^.*$/\%{npcat}#role=a/
relabel ich /^.*$/*LFQ*-\%{num}/

```
とはいえ，それは本来，文の解釈をして，手動で行わなければならないものである．
自動的に行うのは，単なる近似に過ぎない．


### 格標識や後置詞に埋め込まれている量化詞
IPの項ではあるが，格標識や後置詞に埋め込まれているために，
  IP上でスコープをとると明示されていない例が（多く）ある．
```
(IP-MAT (PP-SBJ (NPq#index=2 3人)
                (P が))
        (VB 起きた))
```

これらについても，上と同様に，`*LFQ*`によって，スコープを明示させることにする．

```tsurgeon
/^IP/=ip
  < (
    /^PP/
      < /^(NPd?q.*)#index=(1)(.*)$/#1\%npcat#2\%num#3\%rem=NPqinner
  )
  !: /\*LFQ\*-1/

insert (=lf =ich) >1 ip
relabel lf /^.*$/\%{npcat}#role=a/
relabel ich /^.*$/*LFQ*-\%{num}/

/^IP/=ip
  < (
    /^PP/
      < /^(NPd?q.*)#index=(2)(.*)$/#1\%npcat#2\%num#3\%rem=NPqinner
  )
  !: /\*LFQ\*-2/

insert (=lf =ich) >1 ip
relabel lf /^.*$/\%{npcat}#role=a/
relabel ich /^.*$/*LFQ*-\%{num}/

/^IP/=ip
  < (
    /^PP/
      < /^(NPd?q.*)#index=(3)(.*)$/#1\%npcat#2\%num#3\%rem=NPqinner
  )
  !: /\*LFQ\*-3/

insert (=lf =ich) >1 ip
relabel lf /^.*$/\%{npcat}#role=a/
relabel ich /^.*$/*LFQ*-\%{num}/

/^IP/=ip
  < (
    /^PP/
      < /^(NPd?q.*)#index=(4)(.*)$/#1\%npcat#2\%num#3\%rem=NPqinner
  )
  !: /\*LFQ\*-4/

insert (=lf =ich) >1 ip
relabel lf /^.*$/\%{npcat}#role=a/
relabel ich /^.*$/*LFQ*-\%{num}/

/^IP/=ip
  < (
    /^PP/
      < /^(NPd?q.*)#index=(5)(.*)$/#1\%npcat#2\%num#3\%rem=NPqinner
  )
  !: /\*LFQ\*-5/

insert (=lf =ich) >1 ip
relabel lf /^.*$/\%{npcat}#role=a/
relabel ich /^.*$/*LFQ*-\%{num}/

/^IP/=ip
  < (
    /^PP/
      < /^(NPd?q.*)#index=(6)(.*)$/#1\%npcat#2\%num#3\%rem=NPqinner
  )
  !: /\*LFQ\*-6/

insert (=lf =ich) >1 ip
relabel lf /^.*$/\%{npcat}#role=a/
relabel ich /^.*$/*LFQ*-\%{num}/

```

### 後処理
若い番号から処理する関係でそのままではinverse scopeがデフォルトとなって気持ち悪いため，
最後に昇順に並べ替えを行う．

```tsurgeon
__=lfq
  < *LFQ*-1
  $,, (__=x < /^\*LFQ\*-[2-6]$/)

move lfq $+ x


__=lfq
  < *LFQ*-2
  $,, (__=x < /^\*LFQ\*-[3-6]$/)

move lfq $+ x


__=lfq
  < *LFQ*-3
  $,, (__=x < /^\*LFQ\*-[4-6]$/)

move lfq $+ x


__=lfq
  < *LFQ*-4
  $,, (__=x < /^\*LFQ\*-[5-6]$/)

move lfq $+ x


__=lfq
  < *LFQ*-5
  $,, (__=x < /^\*LFQ\*-6$/)

move lfq $+ x

```
また，変換の都合上関係節のトレースはIPの先頭にあってほしいので，\*LFQ\*より前に来るようにする：

```tsurgeon
__=x
  < *T*
  $,, (__=y < /^\*LFQ\*-[1-9]+$/)

move x $+ y

```

Keyakiの`;*`に相当する`#qinner`素性は，後々の再利用のことも考えて，そのまま残す．


## CPの正規化
CP-QUEについて、助詞がない場合に、空のものを補う。

```tsurgeon
/^CP-QUE/=que 
  !== /#deriv=/
  < (/^IP-SUB/=x !$ /^IP-SUB/) 
  !< P

relabel que /^.*$/={que}#deriv=unary-Q/

```

例：
```
  (CP-QUE (CP|IP ...))
  -> (CP-QUE#deriv=unary-Q (CP|IP ...))
```

このようなことをするのは、question particleがheadにであるためである。
adjunctになるparticleで、空のものについては、補う必要はない。

IP-SUBまたはmulti-sentencesを単独支配するCP-THTについても、同様に空のものを補う。

```tsurgeon
/^CP-THT/=cp 
  !== /#deriv=/
  !< P
  !< *PRO* 

relabel cp /^.*/={cp}#deriv=unary-COMP/

```

## 変換の対象外の枝分かれについて
変換の対象外となる枝分かれは，以下をトップノードとするものである：
- INTJP
- LST
- FRAG
- PRN
- multi-sentence
これらの枝分かれについては，unaryであろうとそのまま維持されるべきであり，relabelしないままにしたいので，
そのことを素性で指定することにする．

### PRN類の正規化
```tsurgeon
/^(INTJP|LST|FRAG|PRN)$/=node
  !== /#deriv=/

relabel node /^.*/={node}#deriv=leave/

```

### `multi-sentence`の正規化
複数文が連なったとき，Keyakiでは，それらの文を束ねて`multi-sentence`ノードを立てている．
我々としては，個々の文を独立したものにしたい（i.e. 個々の文のルートノードを`S`にしたい）ので，
  relabelしないことにする．

```tsurgeon
/^multi-sentence$/=ms
  !== /#deriv=/

relabel ms /^.*/={ms}#deriv=conj-multi-sentence/  

```

## `QUOT`の変換
量化詞`Q`の処理を煩雑にしないため、名称を`ZIT`に変換しておく(これは最終的にrelabelで消失する）

```tsurgeon
QUOT=quot

relabel quot ZIT

```

## *の削除
何らかの理由でIP-ADVを伴わない(CND *)が残っていることがあるので、削除しておく。
他にも消すべき*があるかもしれない。

```tsurgeon
CND=x < *

delete x

```

## Unary branchingの削除
ここに至って、（認可されていない）unary branchingが残っている場合、それらはもはや不要であるので、削除。

```tsurgeon
!/^(VBS|PRN)/ 
  !== /#deriv=/
  !<2 __ 
  <1 (__=y < __ ) 

excise y y

```