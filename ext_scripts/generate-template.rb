#!/usr/bin/ruby
# coding: utf-8

#改行で区切ってcont, prej, diffそれぞれの可能なカテゴリをリストアップする
cont_list = 'N
NP
PP
S
(N/N)
(N\N)
(PP\S)
(S/S)
(S\S)
((PP[s=true]\S)/(PP[s=true]\S))'.delete(" ").split("\n")

prej_list = 'N
PP
(S/S)
(N/N)
(NP/NP)
S
(PP[s=true]\S)
((PP[s=true]\S)/(PP[s=true]\S))
((PP[o1=true]\(PP[s=true]\S))/(PP[o1=true]\(PP[s=true]\S)))'.delete(" ").split("\n")

diff_list = 'N
PP
NP
NUMCLP
(S/S)
(N/N)
(PP[o1=true]\(PP[s=true]\S))
(PP[s=true]\S)
((PP[s=true]\S)/(PP[s=true]\S))
(((PP[s=true]\S)/(PP[s=true]\S))\((PP[s=true]\S)/(PP[s=true]\S)))'.delete(" ").split("\n")


diff_sem = '\X. \C1 D S C0. yori_mp(S(\Y. Y)(\Z. Z)(C1), S(\Y. Y)(\Z. Z)(C0), D)'
no_diff_sem = '\X. \C1 S C0. yori(S(\Y. Y)(C1), S(\Y. Y)(C0))'

diff_sem_kurabe = '\X. \C1 D S C0. kurabe_mp(S(\Y. Y)(\Z. Z)(C1), S(\Y. Y)(\Z. Z)(C0), D)'
no_diff_sem_kurabe = '\X. \C1 S C0. kurabe(S(\Y. Y)(C1), S(\Y. Y)(C0))'


def comp_template(cat, sem)
  label = cat.to_label
  <<-EOS
- &#{label}
  category: #{cat}
  base: より
  semantics: |
    #{sem}
- <<: *#{label}
  base: よりも
- <<: *#{label}
  base: よりは
  EOS
end

def kurabe_template(cat, sem)
  label = cat.to_label + "kurabe"
  <<-EOS
- &#{label}
  category: #{cat}
  base: に比べ
  semantics: |
    #{sem}
- <<: *#{label}
  base: に比べて
- <<: *#{label}
  base: にくらべ
- <<: *#{label}
  base: にくらべて
- <<: *#{label}
  base: と比べ
- <<: *#{label}
  base: と比べて
- <<: *#{label}
  base: とくらべ
- <<: *#{label}
  base: とくらべて
  EOS
end

def expand_rest_trace(cat, label)
  <<-EOS
- <<: *comp-trace-#{label}
  category: #{cat}
  EOS
end

def trace_template(cat_list, label, trace)
  rest_str = cat_list.slice(1..).map { |cat| expand_rest_trace(cat, label) }.join("")
 
  <<-EOS
- &comp-trace-#{label}
  category: #{cat_list.first}
  semantics: \\E. #{trace}
  base: "*TRACE-#{label}1*"
#{rest_str}
  EOS
end

def expand_rest_intro_cont(cat, label)
  <<-EOS
- <<: *comp-intro-#{label}
  category: (S|#{cat})
  EOS
end

def intro_cont_template(cat_list, label, trace)
  cat = cat_list.first
  rest_str = cat_list.slice(1..).map { |cat| expand_rest_intro_cont(cat, label) }.join("")
 
  <<-EOS
- &comp-intro-#{label}
  category: (S|#{cat})
  rule: "|-intro-#{label}1"
  semantics: \\M. lam(#{trace}, M)
#{rest_str}
  EOS
end

def expand_rest_intro_prej(cat_pair, label)
  cont, prej = cat_pair
  <<-EOS
- <<: *comp-intro-#{label}
  category: ((S|#{cont})|#{prej})
  EOS
end

def intro_prej_template(cat_pair_list, label, trace)
  cont, prej = cat_pair_list.first
  rest_str = cat_pair_list.slice(1..).map { |cat_pair| expand_rest_intro_prej(cat_pair, label) }.join("")
 
  <<-EOS
- &comp-intro-#{label}
  category: ((S|#{cont})|#{prej})
  rule: "|-intro-#{label}1"
  semantics: \\M. lam(#{trace}, M)
#{rest_str}
  EOS
end

def expand_rest_intro_diff(cat_pair, label)
  cont, prej, diff = cat_pair
  <<-EOS
- <<: *comp-intro-#{label}
  category: (((S|#{cont})|#{prej})|#{diff})
  EOS
end

def intro_diff_template(cat_pair_list, label, trace)
  cont, prej, diff = cat_pair_list.first
  rest_str = cat_pair_list.slice(1..).map { |cat_pair| expand_rest_intro_diff(cat_pair, label) }.join("")
 
  <<-EOS
- &comp-intro-#{label}
  category: (((S|#{cont})|#{prej})|#{diff})
  rule: "|-intro-#{label}1"
  semantics: \\M. lam(#{trace}, M)
#{rest_str}
  EOS
end


class String
  def to_label
    self.gsub(/\//,"-fs-").gsub(/\\/,"-bs-").delete("/\\|=()[]")
  end
  
end

class Array

  def make_no_diff_cat
    cont, prej = self
    "(((S|#{cont})|((S|#{cont})|#{prej}))|NP)"
  end

  def make_diff_cat
    cont, prej, diff = self
    "((((S|#{cont})|(((S|#{cont})|#{prej})|#{diff}))|DEG)|NP)"
  end
  
end

#デカルト積を作る
cont_prej_pair = cont_list.product(prej_list)
cont_prej_diff_pair = cont_list.product(prej_list, diff_list)

#mapでdiff_cat、no_diff_catに流し込んでカテゴリのリストを作る
no_diff_cat = cont_prej_pair.map(&:make_no_diff_cat)
diff_cat = cont_prej_diff_pair.map(&:make_diff_cat)

no_diff = no_diff_cat.map { |x| comp_template(x, no_diff_sem) }
diff = diff_cat.map { |x| comp_template(x, diff_sem) }

comp = (no_diff | diff).join("\n") 

no_diff_kurabe = no_diff_cat.map { |x| kurabe_template(x, no_diff_sem_kurabe) }
diff_kurabe = diff_cat.map { |x| kurabe_template(x, diff_sem_kurabe) }

kurabe = (no_diff_kurabe | diff_kurabe).join("\n") 


#traceのテンプレートを作る
catlist_label_trace_triples = [cont_list, prej_list, diff_list]
                                .zip(["cont", "prej", "diff"], ["T11", "T21", "T31"])

trace = catlist_label_trace_triples
          .map { |arg| trace_template(*arg) }
          .join("")


#introのテンプレートを作る
#prejとdiffのケースはカテゴリの組をテンプレートに渡さないといけないのでやや複雑になる

intro_cont = intro_cont_template(cont_list, "cont", "T11")
intro_prej = intro_prej_template(cont_prej_pair, "prej", "T21")
intro_diff = intro_diff_template(cont_prej_diff_pair, "diff", "T31")

intro = intro_cont + intro_prej + intro_diff 
  
#全部つなげる  
result = comp + kurabe + trace + intro 

puts result 


