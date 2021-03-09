# Binarization & Head-Comp Detection Tool for ABC Treebank
## 概要
文法関係をマークする．

1. 補部を`#role=c`でマークする．
1. 主要部を`#role=h`でマークする．
3. 主語指向の文末表現を`#role=ac`でマークする．
4. 残りは`#role=a`とマークする（これは，最後にまとめて行われる）．

## 主要部-補部のマーキング

### IP
#### 補部
以下にあるように，文法役割がついているPP（PRDを除く）は補部である．
```
/^IP/ -> /(SBJ|SBJ2|OB1|OB2|LGS)/$#role=c ...
```
NOTE: 文法役割がつくのは，一般的にはPPだけとも限らない．

CP補文（但し，副詞節を除く）もまた補部である．
```
/^IP/ -> /(CP-THT|CP-QUE)/$#role=c ...
```
NOTE: CP-THT-OB1とマークされたり、CP-THTとマークされたりして、
  まちまちであるのて、手修正が必要になるだろう。

さらに，`IP-SMC`も明らかに補部である．

```tsurgeon
/^IP/ !== /#deriv=.+/
  < (
    /(SBJ|SBJ2|OB1|OB2|LGS|CP-THT|CP-QUE|IP-SMC)/=x
    !== /#role/
    !== /ADV/
    )

relabel x /^.*$/={x}#role=c/

```

#### 主要部（述語）
##### 一般的なもの
以下は明らかに述語である．
- `VB`
- `ADJI`
- `ADJN`
- `CAUS`
- `PASS`
- `.*PRD`

```tsurgeon
/^IP/ !== /#deriv=.+/
  < (
    /^(VB|ADJI|ADJN|CAUS|VBP|.*-PRD(#.+)?)$/=x
    !== /#role=h/
  )

relabel x /^.*$/={x}#role=h/ 

```
NOTE: `PRD`（名詞述語文，または，分裂文の焦点）は，当分の間，述語だと思うことにするが，
将来，いくつかの`PRD`を`AX`の補部だとする可能性がある．
（ref. Issue #4）

##### `ADVP`-`AX`の連続
純粋な副詞節としての`ADVP`もあるが，
  `AX`あるいは「だろう」「らしい」に隣接しているような`ADVP`は述語である．

```tsurgeon
/^IP/ !== /#deriv=.+/
  < (/^ADVP$/=x 
        [   $. (AX|MD !$,, AX) 
          | . だろう 
          | . (だろ . う)
          | . /^らし(かろ|かっ|く|い|けれ)$/
          | . /^かもしれ/
        ]
        !== /#role=h/
        ) 
  !< /#role=h/

relabel x /^.*$/={x}#role=h/ 

```

「どうか」「そうか」「そっか」「なるほどね」における「どう」「そう」「そっ」「なるほど」も述語とみなす．

```tsurgeon

/^IP/ !== /#deriv=.+/
  <-1 (ADVP=x 
          < (/^W?ADV$/ < どう|そう|そっ|なるほど) 
          !$ /^(VB|AX|ADJI|ADJN|.P-PRD|P)(#role=.)?$/
  )
  !< /#role=h/

relabel x /^.*$/={x}#role=h/ 

```

#### `AX` (default rule)
`AX`は普通，述語ではないが，他に述語の候補がないとき，
*最左*のものが述語とみなされる．
```tsurgeon
/^IP/ 
  !== /#deriv=.+/
  !< /#role=h/ 
  < (/^AX$/=x !$,, /^AX$/)

relabel x /^.*$/={x}#role=h/

```

#### 主語指向文末表現
主語指向文末表現に対しては，特別に`#role=ac`を与える．
そうすると，範疇変換の際，`<S\S>`の代わりに`<<PPs\S>\<PPs\S>>`が与えられる．

##### 一般のもの
```tsurgeon
__=ac
  !== /#role=/ 
  [ 
    (
      == /VB[02]/
      < /^(((くだ|下|な)(す|さ|せ))|いらっしゃ|参|まい|や|奉)(ら|り|る|れ|ろ|い|っ|え)$/ 
    )
    | (
      == /VB[02]/
      < /^(み|見|終え|申し上げ|まちがえ|間違え|見せ|みせ|おおせ|遅れ|でき|出来)(る|れ|ろ|よ)?$/ 
    )
    | (
      == /VB2/
      < /^お[かきくけこい]$/
    )
    | < /^(いた|致|申)(さ|し|す|せ|そ)$/ 
    | (< /^(つもり|所存)$/ !> /^N/) 
    | (
      !== /VBP/ 
      !== P
      < /^ら?(れ|れる|れれ|れろ|れよ)$/
    ) 
    | < /^(あげ|くれ|おくれ|差し上げ|さしあげ)(る|れ|ろ|よ)?$/
    | < /^(たま|給|損な)(わ|い|う|え|お|っ)$/
    | < /^た(かろ|かっ|く|い|けれ)$/
    | < /^たが[らりるれろっ]$/
    | < ねえ|おやん
    | (< 御覧 == /VB2/)
    | (
      == /VB/
      < /^と[かきくけこい]$/ 
    ) 
  ]

relabel ac /^.*$/={ac}#role=ac/

```

コメント：全部VB2ならまとめて指定したほうがよい．

##### 特別な構文で主語指向になる述語
「VBになる」(主体尊敬表現 お...になる)

```tsurgeon
__=ac
  !== /#role=/
  < /^な[らりるれろっ]$/
  , (に , /^VB(#role=.)?$/)

relabel ac /^.*$/={ac}#role=ac/

```
「VBする」(客体尊敬表現 お...する)

```tsurgeon
VB0=ac
  < せ|さ|し|する|すれ|しろ|せよ
  $, (/^VB(#role=.)?$/ (< (/^お.+[いきぎしじちにひびみりえけげせぜてでねへべめれ]$/ !== おっとり|おじぎ|おしゃべり|お色直し)) | (< /^ご[亜-熙]+$/) | (< お電話))

relabel ac /^.*$/={ac}#role=ac/

```
「お支払いする」については謙譲語と丁寧語で曖昧なので、丁寧語のほうは後に目視で修正する必要がある。

### 名詞句類 1（`NPq?d`）
#### 補部
`NP`または`NPq`は補部．
ただし敬称の「さん」などはこの限りでない(adjunct).

```tsurgeon
/^NPq?d/ 
  !== /#deriv=.+/
  < (
      (/^NPq?$/=x !< (さん|くん|君|さま|様|先生 > (NP $, N|NPR)))
      !== /#role=c/
  )

relabel x /^.*$/={x}#role=c/

```
注意：`/NP/`はNPとNPRの両方にマッチするが，ここではNPRにはマッチしてほしくない．
NPRは主要部であるべきである．

`IP-EMB`と`CP-THT`はみな`NPd`の補部である．

```tsurgeon
/^NPq?d/ 
  !== /#deriv=.+/
  < /^(IP-EMB|CP-THT)$/=x

relabel x /^.*$/={x}#role=c/

```

(2020.11.02) ccg2lambdaのために，Dの主要部性を一度無効にした．
NPdやNPqdのように，d素性を持って範疇が現れることがないので，これらの規則は発動されない（残しても無害である）．

#### 主要部
*最右*の指示詞類が主要部．

```tsurgeon
/^NPq?d/ 
  !== /#deriv=.+/
  < /^(D|WD|PRO|WPRO|NPR)$/=x

relabel x /^.*$/={x}#role=h/

```

### 名詞句類 2（`Nq?`）
#### 主要部
```tsurgeon

N !== /#deriv=.+/
  < (CL=x !$.. CL)
  !< /#role=h/

relabel x /^.*$/={x}#role=h/


/^Nq?/ 
  !== /^Ns$/
  !== /^Nq?d/
  !== /#deriv=.+/
  < (
      (
        /^((Ns|NPR|Q|QN|CL|PRO|WPRO|IP-NML|NUMCLP|Nd?q?|NP|NUM|WNUM)|(PP-REL|MENTION))/=x 
          !< (さん|くん|君|さま|様|先生 > (/^Ns/ $, /^(Ns|NPR)/))
      )
      !$.. /^((Ns|NPR|Q|QN|CL|PRO|WPRO|IP-NML|NUMCLP|Nd?q?|NP|NUM|WNUM)|(PP-REL|MENTION))/
    )
  !< /#role=h/

relabel x /^.*$/={x}#role=h/

/^Nq?/ 
  !== /^Ns$/
  !== /^Nq?d/
  !== /#deriv=.+/
  < (
      /^((Ns|NPR|Q|QN|CL|PRO|WPRO|IP-NML|NUMCLP|Nd?q?|NP|NUM|WNUM)|(PP-REL|MENTION))/=x
      $. (/^Ns/ < (さん|くん|君|さま|様|先生))
    )
  !< /#role=h/

relabel x /^.*$/={x}#role=h/

```

#### 補部
主要部の左にある，然るべき要素はみな`Nq?`の補部である．

```tsurgeon
/^Nq?/ 
  !== /^Nq?d/
  !== /#deriv=.+/
  < (
    /^((Ns|NPR|Q|QN|CL|PRO|WPRO|IP-NML|NUMCLP|Nd?q?|NP|NUM|WNUM)|(IP-EMB|CP-THT|IP-SUB))/=x 
    $.. /#role=h/
    !== /#role=/
  )

relabel x /^.*$/={x}#role=c/

```

### 名詞句類 3（`NUMCLP`）
#### 主要部
主要部は最右の`CL`である．
`CL`がない場合，pretreatmentsにより，それは，relabelingの対象外である．
pretreatmentsにより，量化的でない`NUMCLP`は`N`に貼り替えられていることに注意．

```tsurgeon
/^NUMCLP/ 
  !== /#deriv=.+/
  < (
    /^CL/=x
    !$.. /CL/
  )
  !< /#role=h/

relabel x /^.*$/={x}#role=h/

```

#### 補部
主要部の左にある，然るべき要素はみな補部である．
ここでは`NUMCLP`のみを対象にしている(`N`についてはすでに上で同様の処理を行っているため)．

```tsurgeon
/^NUMCLP/
  !== /#deriv=.+/
  < (
    __=x
    $.. /#role=h/
    !== /#role=/
  )

relabel x /^.*$/={x}#role=c/

```

### ADVP
以下はその主要部である．
- `ADV`
- `ADVP`
- `WADV`
- `ADJI`
- `ADJN`

```tsurgeon
/^ADVP/
  !== /#deriv=.+/
  < /^(ADV|ADVP|WADV|ADJI|ADJN)$/=x

relabel x /^.*$/={x}#role=h/

```

### ADJP
```tsurgeon
/^ADJP/ 
  !== /#deriv=.+/
  < /^(ADJI|ADJN)$/=x

relabel x /^.*$/={x}#role=h/

```

### CP-QUE

#### 「かどうか」
`IP`または`CP`を補部とし，「どう」を主要部とする．
```tsurgeon
/^CP-QUE/ 
  !== /#deriv=.+/
  < (/IP|CP/=x $.. ((P < か) $. ((WADV=y < どう) $. (P < か)))) 
  !< /#role=h/

relabel x /^.*$/={x}#role=c/
relabel y /^.*$/={y}#role=h/

```

#### 通常の場合
```tsurgeon
/^CP-QUE/ 
  !== /#deriv=.+/
  < /IP|CP/=x 
  < /^(P)$/=y 
  !< /#role=h/

relabel x /^.*$/={x}#role=c/
relabel y /^.*$/={y}#role=h/

```

#### デフォルト
最右を主要部とする
CP-QUE -> ... __-h
```tsurgeon
/^CP-QUE/ 
  !== /#deriv=.+/
  <-1 (__=x < __) 
  !< /#role=h/

relabel x /^.*$/={x}#role=h/

```

### 「と」に導かれるCP-THT

```tsurgeon
/^CP-THT/ 
  !== /#deriv=.+/
  < /^(IP-(SUB|IMP|MAT|SMC)|CP-(QUE|FINAL|EXL)|multi-sentence|INTJP|FRAG)$/=y 
  < (P=x < と|っていう|ていう|という|ちゅう)

relabel x /^.*$/={x}#role=h/
relabel y /^.*$/={y}#role=c/

```


### CP（その他）
`CP-FINAL`，`CP-THT`，`CP-EXL`の3種類がある．

主要部としては，`IP`，`CP`，`multi-sentence`，`INTJP`の4
種類がある．
```tsurgeon
/^CP-(FINAL|THT|EXL)/ 
  !== /#deriv=.+/
  < /^(IP-(SUB|IMP|MAT|SMC)|CP-(QUE|FINAL|EXL|THT)|multi-sentence|INTJP|FRAG)/=x
  < /^(P)$/=y
  !< /#role=h/

relabel x /^.*$/={x}#role=c/
relabel y /^.*$/={y}#role=h/

```

#### デフォルト
最右を主要部とする．
```tsurgeon
/^CP-(FINAL|THT|EXL)/ 
  !== /#deriv=.+/
  !< /#role=h/
  <-1 (__=x < __) 

relabel x /^.*$/={x}#role=h/

```

### PP
内部のバリエーションは雑多である．

#### `ADVP`-`P`
この場合の`P`は付加詞として扱う．

```tsurgeon
/^PP/ 
  !== /#deriv=.+/
  !< /#role=h/ 
  <1 (/^ADVP$/=x $. /^P$/)

relabel x /^.*$/={x}#role=h/

```

#### 補部
補部として以下がありうる：

- `IP-ADV`
- `IP-NML`
- `DP` （`NP`, `NPd`, `NPq`, `NPdq`は，PPの元にはないはずだが，一応付けておく）
- `CP`類，`multi-sentence`

```tsurgeon
/^PP/ 
  !== /#deriv=.+/
  !< /#role=/ 
  < /^(IP-(ADV|NML)|DP|NPd?q?|multi-sentence|CP)/=x

relabel x /^.*$/={x}#role=c/

```

#### 主要部
PP-(SCON|CONJ|CND)と，とりたて助詞の構造（特に，「～しても」のようなもの）に関しては，
補文節を主要部として，とりたて詞を，補文節を修飾するようなもの（すなわち，adjunct）だとする．

```tsurgeon
/^PP.*$/
  !== /#deriv=.+/
  !< /#role=h/
  < (
    /^PP-(SCON|CONJ|CND)/=x
    $.. /^P/
  )

relabel x /^.*$/={x}#role=h/

```

最左の`P`が主要部である．
ただし，格助詞にとりたて助詞が先行する構造の場合は，
格助詞を主要部とする(pretreatmentsで処理)．

```tsurgeon
/^PP.*$/ 
  !== /#deriv=.+/
  !< /#role=h/ 
  < (/^P$/=x !$,, /^P$/)

relabel x /^.*$/={x}#role=h/

```

#### デフォルト
最右のものを主要部とする．
```tsurgeon
/^PP.*$/ 
  !== /#deriv=.+/
  !< /#role=h/ 
  <-1 (__=x < __)

relabel x /^.*$/={x}#role=h/

```

### 変換の対象外となるもの
挿入句，感嘆句など，主節の意味計算に直接は関与しない，
かつ，直接支配する部分木の種類が雑多で，内心構造を持たないものについては，
変換の対象外とする．
変換の対象外となるようにするためには，子ノードに `#role=h` 主要部マーキングを**入れない**ようにする．

変換の対象外である句のリスト：
- INTJP
- LST
- FRAG
- PRN

## 後処理
### 複数の主要部マーキングがあった場合
**最右のものを残して**削除する．
```tsurgeon
/#role=h/=e $.. /#role=h/

relabel e /^(.*)#role=h/$1/

```

例：
```
  (... X#role=h ... Y#role=h ...)
  -> (... X ... Y#role=h ...)
```

### 付加詞のマーキング
主要部が指定されているlocal treeの子ノードで，
マーキングがまだなされていないものは，
みな付加詞であり，`#role=a`を付与する．
```tsurgeon
__
  <2 __
  < /#role=h/
  < (__=child !== /#role=/)
     
relabel child /^.*$/={child}#role=a/

```
NOTE: at this point every node should be marked either #role=h, #role=c or #role=a. No further change.
