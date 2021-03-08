# Modifications after dependency marking
## スクランブリングの処理
### 概要
スクランブリングを扱う．

1. スクランブリングを検出して，述語にマークする．
仮定する項のhierarchyは以下のとおり：
SBJ > SBJ2 > LGS > OB1 > OB2 > THT|QUE|SMC

2. スクランブリングが検出された木について，述語の項を検出し，canonicalな順番で入れ直す．

3. さらに，スクランブリングをマークされた述語の右に現れる要素も全て下ろしていく．


### OB2
```tsurgeon

/^(VB|ADJN|ADJI|CAUS|VBP|AX).*#role=h/=x $,, (/(THT|QUE|SMC).*#role=c/ !== /ADV/ $.. /OB2.*#role=c/) !== /__cat_SCR/

relabel x /^(.*)$/={x}__cat_SCR/

```

### OB1

```tsurgeon

/^(VB|ADJN|ADJI|CAUS|VBP|AX).*#role=h/=x $,, (/(THT|QUE|SMC|OB2).*#role=c/ !== /ADV/ $.. /OB1.*#role=c/) !== /__cat_SCR/

relabel x /^(.*)$/={x}__cat_SCR/

```

### LGS

```tsurgeon

/^(VB|ADJN|ADJI|CAUS|VBP|AX).*#role=h/=x $,, (/(THT|QUE|SMC|OB2|OB1).*#role=c/ !== /ADV|;\*/ $.. /LGS.*#role=c/) !== /__cat_SCR/

relabel x /^(.*)$/={x}__cat_SCR/

```


### SBJ2

```tsurgeon

/^(VB|ADJN|ADJI|CAUS|VBP|AX).*#role=h/=x $,, (/(THT|QUE|SMC|OB2|OB1|LGS).*#role=c/ !==/ADV|;\*/ $.. /SBJ2.*#role=c/) !== /__cat_SCR/

relabel x /^(.*)$/={x}__cat_SCR/

```


### SBJ

```tsurgeon

/^(VB|ADJN|ADJI|CAUS|VBP|AX).*#role=h/=x $,, (/(THT|QUE|SMC|OB2|OB1|LGS|SBJ2).*#role=c/ !== /ADV/ $.. /SBJ[^2]*#role=c/) !== /__cat_SCR/

relabel x /^(.*)$/={x}__cat_SCR/

```

% IP-SMCの中にLGSや間接受動のAgentとしてのOB1が登場する場合の処理
ICHの処理が必要

### マークされた述語に対する処理
#### unary branchを立てる

```tsurgeon
/^(.*)__cat_SCR/#1\%pred=x < (__=y !< __) 

createSubtree predicate=z y
relabel z /^(.*)$/\%{pred}/

```

#### unary branchの下に項を格納していく
IP-SMCの場合のみ，主語の有無で場合分けをする(pretreatmentで主語は補われてしまっているので，実質的にはその主語が*PRO*を支配するかどうかで判定する)．
本来はIP-SMCは主語をもたないはずだが，「...が...てほしい」構文や，
「...を...にVされる」のようなスクランブリングの絡むケースでは主語をもつことを余儀なくされている．

```tsurgeon
/^(.*)__cat_SCR/=x $,, (/^(.*THT.*#role=c)$/#1\%arg !== /ADV/) !<  /^(.*THT.*#role=c)$/#1\%arg !== /__THTFIN_/

insert (ARG=z *PRO*) >1 x
relabel x /^(.*)$/$1__THTFIN_/
relabel z /^(.*)$/\%{arg}/

/^(.*)__cat_SCR/=x $,, (/^(.*QUE.*#role=c)$/#1\%arg !== /ADV/) !<  /^(.*QUE.*#role=c)$/#1\%arg !== /__QUEFIN_/

insert (ARG=z *PRO*) >1 x
relabel x /^(.*)$/$1__QUEFIN_/
relabel z /^(.*)$/\%{arg}/

/^(.*)__cat_SCR/=x $,, (/^(.*SMC.*#role=c)$/#1\%arg < (/SBJ#role=/ !< *PRO*) ) !<  /^(.*SMC.*#role=c)$/#1\%arg !== /__SMCFIN_/

insert (ARG=z *PRO*) >1 x
relabel x /^(.*)$/$1__SMCFIN_/
relabel z /^(.*)$/\%{arg}/

/^(.*)__cat_SCR/=x $,, (/^(.*SMC.*#role=c)$/#1\%arg=y < (/SBJ#role=/ < *PRO*) < (/OB1#role=/ < *PRO*)) !<  /^(.*SMC.*#role=c)$/#1\%arg !== /__SMCFIN_/

insert (ARG=z (=sbj *PRO*)(=ob1 *PRO*)(=v *PRO*)) >1 x
relabel x /^(.*)$/$1__SMCFIN_/
relabel z /^(.*)$/\%{arg}/
relabel sbj /^.*$/PP-SBJ#role=c/
relabel ob1 /^.*$/PP-OB1#role=c/
relabel v /^.*$/VB#role=h/

/^(.*)__cat_SCR/=x $,, (/^(.*SMC.*#role=c)$/#1\%arg=y < (/SBJ#role=/ < *PRO*) !< (/OB1#role=/ < *PRO*)) !<  /^(.*SMC.*#role=c)$/#1\%arg !== /__SMCFIN_/

insert (ARG=z (=sbj *PRO*)(=v *PRO*)) >1 x
relabel x /^(.*)$/$1__SMCFIN_/
relabel z /^(.*)$/\%{arg}/
relabel sbj /^.*$/PP-SBJ#role=c/
relabel v /^.*$/VB#role=h/

/^(.*)__cat_SCR/=x $,, /^(.*OB2.*#role=c)$/#1\%arg !<  /^(.*OB2.*#role=c)$/#1\%arg !== /__OB2FIN_/

insert (ARG=z *PRO*) >1 x
relabel x /^(.*)$/$1__OB2FIN_/
relabel z /^(.*)$/\%{arg}/

/^(.*)__cat_SCR/=x $,, /^(.*OB1.*#role=c)$/#1\%arg !<  /^(.*OB1.*#role=c)$/#1\%arg !== /__OB1FIN_/

insert (ARG=z *PRO*) >1 x
relabel x /^(.*)$/$1__OB1FIN_/
relabel z /^(.*)$/\%{arg}/

/^(.*)__cat_SCR/=x $,, /^(.*LGS.*#role=c)$/#1\%arg !<  /^(.*LGS.*#role=c)$/#1\%arg !== /__LGSFIN_/

insert (ARG=z *PRO*) >1 x
relabel x /^(.*)$/$1__LGSFIN_/
relabel z /^(.*)$/\%{arg}/

/^(.*)__cat_SCR/=x $,, /^(.*SBJ2.*#role=c)$/#1\%arg !<  /^(.*SBJ2.*#role=c)$/#1\%arg !== /__SBJ2FIN_/

insert (ARG=z *PRO*) >1 x
relabel x /^(.*)$/$1__SBJ2FIN_/
relabel z /^(.*)$/\%{arg}/

/^(.*)__cat_SCR/=x $,, /^(.*SBJ.*#role=c)$/#1\%arg !<  /^(.*SBJ.*#role=c)$/#1\%arg !== /__SBJFIN_/

insert (ARG=z *PRO*) >1 x
relabel x /^(.*)$/$1__SBJFIN_/
relabel z /^(.*)$/\%{arg}/

```

### 文末表現の移動

```tsurgeon
/__cat_SCR/=x $. __=y

move y >-1 x

```


### 文ノードおよびSCRマーカーを挿入(relabelingのための処理)
```tsurgeon
/__cat_SCR/=x > /^(.*)#role=.$/#1\%sent !<   /^(.*)#role=c$/#1\%sent

adjoinH ( SENT=z@) x
relabel z /^(.*)$/\%{sent}#role=c/
insert (=ph __lex_SCR) $- z
relabel ph /^.*$/P#role=h/

/__cat_SCR/=x > /^(.*[^ach])$/#1\%sent !<   /^(.*)#role=c$/#1\%sent

adjoinH ( SENT=z@) x
relabel z /^(.*)$/\%{sent}#role=c/
insert (=ph __lex_SCR) $- z
relabel ph /^.*$/P#role=h/


```


### 直接受動文の処理
#### STEP1
受動マーカーをSCR下に下ろし，さらにSCRに受動のマーキングをする．
これに基づいて受動マーカーより右の述語もSCR下に下ろしてゆく．

```tsurgeon
__ < (/^IP-SMC/ $. /^VBP/=pass < (/cat_SCR/=scr < /^IP-SMC/ !== /PSS/))

move pass >-1 scr
relabel scr /^(.*)$/$1__PSS_/

__ < (/^IP-SMC/ $. __=predicate < (/cat_SCR/=scr < /^IP-SMC/ == /PSS/))

move predicate >-1 scr

```
#### STEP2
SRC直下に最終的にほしい文のカテゴリーをもつノードをコピーして挿入する（これを「下の文」と呼ぶことにする）．
また，そのような（コピー元の）文の直下にあるIP-SMCを削除する．

```tsurgeon
/^(.*)#role=.$/#1\%sent <-1 (/^IP-SMC/=x < (/PSS/=y < (__=w < /lex_SCR/)))

adjoinH ( SENT=z@) y
relabel z /^(.*)$/\%{sent}#role=c/
move w >-1 y
excise x x


/^(.*[^ach])$/#1\%sent <-1 (/^IP-SMC/=x < (/PSS/=y < (__=w < /lex_SCR/)))

adjoinH ( SENT=z@) y
relabel z /^(.*)$/\%{sent}#role=c/
move w >-1 y
excise x x

```

#### STEP3
SCRの情報ならびにもとの文の（受動文カテゴリー形成用に挿入された）*PRO*の存在を手がかりに，
下の文にいる受動マーカーのカテゴリーを決定するための項を挿入していく．
この際，もとの文の*PRO*を削除し、主語以外については削除したという記録をSCRのラベル上で行う．
また，下の文内のIP-SMCに(PP-LGS *PRO*)が入っている場合は，削除する．

```tsurgeon
/^.*(OB1|OB2|THT).*$/#1\%cat=x < *PRO* $ /^.*SCR.*__(OB1|OB2|THT)FIN_.*PSS.*$/=y $ (/SBJ/=z < *PRO* !== /SBJ2/)

delete x
delete z
relabel y /^(.*)$/$1__N\%{cat}_/

/^.*(OB1|OB2|THT).*$/#1\%cat=x < *PRO* $ /^.*SCR.*__(OB1|OB2|THT)FIN_.*PSS.*$/=y !$ (/SBJ/ < *PRO* !== /SBJ2/)

delete x
relabel y /^(.*)$/$1__N\%{cat}_/

/^IP-SMC/ $. /VBP/ < (/LGS/=x < *PRO*)

delete x

/SCR_.+PSS/=y <1 __=x == /THT/ !== /NTHT/

insert (=pro *PRO*) >1 x
relabel y /^(.*)$/$1__NTHT_/
relabel pro /^.*$/CP-THT#role=c/

/SCR_.+PSS/=y <1 __=x == /OB2/ !== /NOB2/

insert (=pro *PRO*) >1 x
relabel y /^(.*)$/$1__NOB2_/
relabel pro /^.*$/PP-OB2#role=c/

/SCR_.+PSS/=y <1 __=x == /OB1/ !== /NOB1/

insert (=pro *PRO*) >1 x
relabel y /^(.*)$/$1__NOB1_/
relabel pro /^.*$/PP-OB1#role=c/

/SCR_.+PSS/=y <1 __=x == /LGS/ !== /NLGS/

insert (=pro *PRO*) >1 x
relabel y /^(.*)$/$1__NLGS_/
relabel pro /^.*$/PP-LGS#role=c/

/SCR_.+PSS/=y <1 __=x $,, /LGS/ !== /NLGS/

insert (=pro *PRO*) >1 x
relabel y /^(.*)$/$1__NLGS_/
relabel pro /^.*$/PP-LGS#role=c/

/SCR_.+PSS/=y <1 __=x == /SBJ/ !== /NSBJ/

insert (=pro *PRO*) >1 x
relabel y /^(.*)$/$1__NSBJ_/
relabel pro /^.*$/PP-SBJ#role=c/

```

#### STEP4
残った（残っているべき）*PRO*に関する後処理(文頭にもっていく)

```tsurgeon
__=x < *PRO* !$.. (__ < *PRO*) $, (__ !< *PRO*|*T*) > (__=y !<1 (__ < *T*)) $.. /PSS/

move x >1 y

__=x < *PRO* !$.. (__ < *PRO*) $, (__ !< *PRO*|*T*) > (__=y <1 (__ < *T*)) $.. /PSS/

move x >2 y

```

#### STEP5
スクランブリングについての拡張タグを削除．

```tsurgeon
/^(.*)(__cat_SCR|__....?FIN_|__PSS_|__N..._)$/#1\%main=x

relabel x /^.*$/\%{main}/

__=p < (__=c <: /^__lex_SCR$/)

relabel p /^.*$/={p}#deriv=unary-scr/
delete c

```

## 句読点
句読点を「美しい」位置に移動する．

### 初期化：空要素との位置関係
これまでの処理で，空要素`/^__lex/`を挿入することがあった．
（注：2020/08/31時点では，このような空要素は `__lex_pred` しかない．）
これは，文法上存在すると考えるべきもので，発音されないもの（例：格助詞の省略）を
表すものである．
仮に，空要素が発音されるものだとすれば，
句読点はそれよりも後ろに打たれるであろう
（実際，主要部であることがほとんどなので，ほとんどの場合そうである）．

従って，句読点が，常に空要素よりも右に位置するように変形を行うべきである．
ただし，別の左端の`__lex`を飛び越えてまですることはない．

```tsurgeon
/^(PU|LRB|RRB|SYM)/=punc
    . (
        __=empty 
            < /^__lex/
            $, __
    )
  
move empty $+ punc

```

例：
```
(XX (PU ．)
    (YY __lex_AA)
    (ZZ __lex_BB)
    ...)
->
(XX (YY __lex_AA)
    (ZZ __lex_BB)
    (PU ．)
    ...)
```

### 疑問文における句読点のlowering
疑問文と感嘆文の適切な意味表示を得るために，
句読点が`IP-SUB`とsisterになっていると不都合が生じるため，
全て`IP-SUB`の下に収める．
「ね」などの疑問文で使えるが必ずしも疑問の意味を表さない終助詞をどうするかは保留．

```tsurgeon
/^IP-SUB/=sub $. /^(PU|RRB)/=pu > /^CP-(QUE|EXL)/

move pu >-1 sub

/^IP-SUB/=sub $, /^(LRB|SYM|LS)/=pu > /^CP-(QUE|EXL)/

move pu >1 sub

```

### （閉じる）句読点の右端化
右端にあるのが望ましい句読点（`LRB`は該当しない）で，
そうなっていないものであって，
何かしらの右端とすることができるものは，そのように句読点を移動する．

```tsurgeon
__=left
  <2 (__ < __)
  . (
    /^(PU|RRB|SYM)/=punc
    $. __
  )

move punc >-1 left

```

例：
```
(IP-MAT (CP-THT (IP-SUB 太郎は遊んでばかりだ)
                (PU ，)
                (P と)
        (PP-SBJ 花子が)
        ...)
->
(IP-MAT (CP-THT (IP-SUB 太郎は遊んでばかりだ (PU ，))
                (P と)
        (PP-SBJ 花子が)
        ...)
```

### 右端句読点の繰り上げ
Ancestorに#role素性があるか否かで場合分け．
ただし、`IP-SUB`に支配されている場合は繰り上げない。

```tsurgeon
/^([^#]*)(.*)(#role=[^#]+)(.*)/#1\%aCat#2\%aPreRole#3\%aRole#4\%aPostRole=ancestor
  $. __
  <<- (
    /^(PU|LRB|RRB|SYM)(.*)#role=[^#]+(.*)/#1\%pCat#2\%pPreRole#3\%pPostRole=punc
    > (__ <3 __)
    !> /^IP-SUB/ 
  )

adjoinF (=ancestoradj @) ancestor
relabel ancestoradj /^.*$/\%{aCat}\%{aRole}/
relabel ancestor /^.*$/\%{aCat}\%{aPreRole}#role=h\%{aPostRole}/
move punc >-1 ancestoradj
relabel punc /^.*$/\%{pCat}\%{pPreRole}#role=a\%{pPostRole}/


/^([^#]*)/#1\%aCat=ancestor
  !== /#role/
  $. __
  <<- (
    /^(PU|LRB|RRB|SYM)(.*)#role=[^#]+(.*)/#1\%pCat#2\%pPreRole#3\%pPostRole=punc
    > (__ <3 __)
    !> /^IP-SUB/
    )

adjoinF (=ancestoradj @) ancestor
relabel ancestoradj /^.*$/\%{aCat}/
relabel ancestor /^.*$/\%{aCat}#role=h/
move punc >-1 ancestoradj
relabel punc /^.*$/\%{pCat}\%{pPreRole}#role=a\%{pPostRole}/

```


## 等位接続
等位接続構造(NP#deriv=conj (NP (N ...)) ...)の中の，中間NPを削除する．
```tsurgeon
/^NP.*#deriv=conj/  < (/^NP.*deriv=unary-NP-type-raising/=x <: /^N/) !< /^NPq/

excise x x
```