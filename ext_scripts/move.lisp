;#!/usr/bin/sbcl --script
(require :sb-cltl2)
(require :uiop)
(require :asdf)
(require :cl-ppcre)
(require :fiveam)

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; (cat cont) を ^cont.cat みたいに書くためのマクロ
;;
;;https://sile.hatenablog.jp/entry/20090628/1246187355

(defun decompose-fn (sym)
  (mapcar #'intern (cl-ppcre:split "@" (string sym))))

(defun get-fn (sym)
  (car (decompose-fn sym)))

(defun get-fnargs (sym)
  (cdr (decompose-fn sym)))

;; ドット表記の関数呼び出しを、S式に変換
;; ^arg2.fn@arg1 のような表記ができるように拡張
(defun read-dot-exprs (stream)
  (reduce (lambda (arg fn) (if (get-fnargs fn)
			       (append (cons (get-fn fn) (get-fnargs fn)) (list arg))
			     (list (get-fn fn) arg)))
	  (mapcar #'intern
		  (cl-ppcre:split "\\." (symbol-name (read stream))))))

;; オリジナル
;; (defun read-dot-exprs (stream)
;;   (reduce (lambda (arg fn) `(,fn ,arg))
;; 	  (mapcar #'intern
;; 		  (split-by-char #\. (symbol-name (read stream))))))

;; リードマクロ読み込み
(set-macro-character #\^
  (lambda (stream c)
    (declare (ignore c))
    (read-dot-exprs stream)))


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defparameter trees nil)
(defparameter test2 nil)

(defparameter filename (cadr *posix-argv*))
;(defparameter filename "sample.psd")

(with-open-file (in filename :direction :input)
		(let ((*readtable* (copy-readtable *readtable*)))
		  (setf (readtable-case *readtable*) :preserve)
		  (loop (let ((buff (read in nil)))
			  (if (not buff) (return))
			  (setq trees (append trees (list buff)))))))

;;Sa, Se, Sm, Srel, Ssub

(defmacro defmacro_s_comp=1 (stype)
  (let* ((node-label (intern (concatenate 'string stype "__comp=1.root")))
	 (node-label-new (intern (concatenate 'string stype "__comp=1.root+"))))
    `(defmacro ,node-label (&rest childs)
       `(move-comp1 (,',node-label-new ,@childs)))))

(defmacro_s_comp=1 "Sa")
(defmacro_s_comp=1 "Se")
(defmacro_s_comp=1 "Sm")
(defmacro_s_comp=1 "Srel")
(defmacro_s_comp=1 "Ssub")


(defmacro defmacro_s_comp=1_alt (stype rule_name)
  (let* ((node-label (intern (concatenate 'string stype "__comp=1.root" rule_name)))
	 (node-label-new (intern (concatenate 'string stype "__comp=1.root+" rule_name))))
    `(defmacro ,node-label (&rest childs)
       `(move-comp1 (,',node-label-new ,@childs)))))

(defmacro_s_comp=1_alt "Sa" "__deriv=>")
(defmacro_s_comp=1_alt "Se" "__deriv=>")
(defmacro_s_comp=1_alt "Sm" "__deriv=>")
(defmacro_s_comp=1_alt "Srel" "__deriv=>")
(defmacro_s_comp=1_alt "Ssub" "__deriv=>")

(defmacro_s_comp=1_alt "Sa" "__deriv=<")
(defmacro_s_comp=1_alt "Se" "__deriv=<")
(defmacro_s_comp=1_alt "Sm" "__deriv=<")
(defmacro_s_comp=1_alt "Srel" "__deriv=<")
(defmacro_s_comp=1_alt "Ssub" "__deriv=<")


(defmacro move-comp1 (s)
  (let* ((cont (car (find-nodes "comp=1\.cont" s)))
	 (prej (car (find-nodes "comp=1\.prej" s)))
	 (diff (car (find-nodes "comp=1\.diff" s)))
	 (diff-mvd (if diff (relabel "DEG__deriv=unary-unknown__comp=1.diff" diff)))
	 (prej-mvd (if diff (relabel-prej-with-diff prej diff
						    (if cont (vs ^s.cat ^cont.cat)
						      ^s.cat) "__deriv=|<__comp=1.prej")
		      (relabel-prej-no-diff prej (if cont (vs ^s.cat ^cont.cat)
						   ^s.cat) "__deriv=|<__comp=1.prej"))))
    (reduce #'(lambda (base filler)
		(let ((result-cat
		      (cond (^filler.contp (+s ^s.cat "__deriv=|<__comp=1.cont.moved"))
			    (^filler.prejp (+s (reduce #'vs (clist ^cont.cat ^diff-mvd.cat)
							   :initial-value ^s.cat) "__deriv=|>__comp=1.prej.moved"))
			    (^filler.diffp (+s (reduce #'vs (clist ^cont.cat)
							   :initial-value ^s.cat) "__deriv=|<__comp=1.diff.moved")))))
		(merge-trees result-cat filler base)))
	    (clist prej-mvd diff-mvd cont)
	    :initial-value (reduce #'remove-and-bind0 (clist cont prej diff) :initial-value s))))

(defun contp (tree)
  (equal ^tree.filler-type "cont"))

(defun prejp (tree)
  (equal ^tree.filler-type "prej"))

(defun diffp (tree)
  (equal ^tree.filler-type "diff"))

(defun treep (sexp)
  (or (symbolp sexp)
      (numberp sexp)
      (and (symbolp (car sexp))
	   (let ((l (mapcar #'treep (cdr sexp))))
	     (and l (not (member nil l)))))))

(defun truep (x) (not (not x)))

(defun bind (cat type tree)
  (let* ((newcat (vs ^tree.cat cat))
	 (suffix (concatenate 'string "__comp=1." type ".bind"))
	 (newlabel (+s newcat suffix)))
  `(,newlabel ,tree)))

(defun merge-trees (cat left-tree right-tree)
  (if left-tree
      `(,cat ,left-tree ,right-tree)
    right-tree))


(defun remove-and-bind (cat type tree)
  (let* ((tag (concatenate 'string "comp=1." type))
	 (trace (make-trace cat type)))
    (bind cat type (replace-nodes tag trace tree))))


(defun remove-and-bind0 (tree subtree)
  (remove-and-bind ^subtree.cat ^subtree.filler-type tree))

(defun filler-type (tree)
  (cl-ppcre:regex-replace "__deriv=.*$"
			  (cadr (cl-ppcre:split "\\." ^tree.get-suffix)) ""))

(defun make-trace (cat type)
  (list (intern (concatenate 'string cat "__comp=1." type))
	(intern (concatenate 'string "*TRACE-" type "1*"))))


(defun relabel-prej-with-diff (prej diff cont-bound-cat suffix)
  (let* ((yori-p-cat (vs (vs cont-bound-cat "DEG") (vs2 cont-bound-cat ^prej.cat ^diff.cat)))
	 (yori-arg (cadr prej))
	 (yori (caddr prej))
	 )
    `(,(+s yori-p-cat suffix)
      ,yori-arg
      ,(relabel (vs yori-p-cat ^yori-arg.cat) yori))))

(defun relabel-prej-no-diff (prej cont-bound-cat suffix)
  (let* ((yori-p-cat (vs cont-bound-cat (vs cont-bound-cat ^prej.cat)))
	 (yori-arg (cadr prej))
	 (yori (caddr prej))
	 )
    `(,(+s yori-p-cat suffix)
      ,yori-arg
      ,(relabel (vs yori-p-cat ^yori-arg.cat) yori))))


(defun vs (res arg)
  (concatenate 'string "<" res "|" arg ">"))

(defun vs2 (res arg1 arg2)
  (vs (vs res arg1) arg2))

(defun add-suffix (label str)
  (intern (concatenate 'string (string label) str)))

(defun +s (label str)
  (add-suffix label str))

(defun remove-suffix (label)
  (cl-ppcre:regex-replace "_.*$" label ""))

(defun remove-cat (label)
  (cl-ppcre:regex-replace "^.*?__" label ""))

(defun get-label (tree)
  (if (and tree ^tree.listp) ^tree.car.string.remove-suffix))

(defun cat (tree)
  ^tree.get-label)

(defun get-suffix (tree)
  (if ^tree.listp ^tree.car.string.remove-cat))

(defun relabel (label tree)
  (if ^tree.listp (cons ^label.intern ^tree.cdr)))

  
(defun flatten (list-of-lists) 
    (apply #'append list-of-lists))

(defun compact (list)
    (remove nil list))

(defun clist (&rest args)
    (remove nil args)) 
    

(defun find-nodes (label tree)
  "labelとマッチするtreeのサブツリーのリストを返す"
  (if (cl-ppcre:scan label ^tree.car.string)
      (list tree)
    ^tree.cdr.find-nodes-all@label))

(defun find-nodes-all (label trees)
  (flatten (compact (mapcar #'(lambda (x) (and ^x.listp
					       ^x.find-nodes@label)) trees))))

(defun remove-nodes (label tree)
  "treeからlabelとマッチするサブツリーを削除"
    (if (cl-ppcre:scan label ^tree.car.string) nil
      (cons ^tree.car (remove-nodes-all label ^tree.cdr))))

(defun remove-nodes-all (label trees)
  (mapcar #'(lambda (x) (if ^x.listp
			    ^x.remove-nodes@label
			  x))
	  trees))

(defun replace-nodes (label subtree tree)
  "treeのlabel位置にsubtreeを埋め込む"
  (if (cl-ppcre:scan label ^tree.car.string)
      subtree
    (cons ^tree.car (replace-nodes-all label subtree ^tree.cdr))))

(defun replace-nodes-all (label subtree trees)
  (mapcar #'(lambda (x) (if ^x.listp
			    ^x.replace-nodes@label@subtree
			  x))
	  trees))


(5am:test my-test
	  "test"
	  (let* ((tree2 (cadr trees))
		 (tree '(TOP
 (|Sm|
  (|<Sm/Sm>|
   (|<Sm/Sm>|
    (|Sa| (|PPs| (|NPq| (N 妻)) (|<NP\\PPs>| が))
     (|<PPs\\Sa>|
      (|<<PPs\\Sa>/<PPs\\Sa>>| (|NPq| (N 仕事))
       (|<NP\\<<PPs\\Sa>/<PPs\\Sa>>>| に))
      (|<PPs\\Sa>| 精出す)))
    (|<Sa\\<Sm/Sm>>| 一方))
   (|<<Sm/Sm>\\<Sm/Sm>>| 、))
  (|Sm__comp=1.root| (|PPs__comp=1.cont| (NP (N 赤沼)) (|<NP\\PPs>| は))
                    (|<PPs\\Sm>|
                     (|<<PPs\\Sm>/<PPs\\Sm>>__comp=1.prej| (NP (N それ))
                      (|<NP\\<<PPs\\Sm>/<PPs\\Sm>>>| より))
                     (|<PPs\\Sm>| (|<<PPs\\Sm>/<PPs\\Sm>>__comp=1.diff| もっと)
                      (|<PPs\\Sm>| (|<PPs\\Sm>__comp=1.deg| 忙しい)
                       (|<Sm\\Sm>| 。))))))
 (ID |5_BCCWJ-ABC-aa-simple|)))
		 
		 (tree-no-diff '(TOP
 (|Sm__comp=1.root|
  (|<Sm/Sm>__comp=1.prej|
   (|NPq| (<NP/NP> (N 剣) (|<N\\<NP/NP>>| や)) (|NPq| (N 刀)))
   (|<NP\\<Sm/Sm>>| (|<NP\\<Sm/Sm>>| より) (|<<Sm/Sm>\\<Sm/Sm>>| も)))
  (|Sm|
   (|PPs__comp=1.cont| (|NPq| (N (<N/N> (NP (N 矛)) (|<NP\\<N/N>>| の)) (N 方)))
    (|<NP\\PPs>| が))
   (|<PPs\\Sm>| (|PPo1| (NP (N 武威)) (|<NP\\PPo1>| が))
    (|<PPo1\\<PPs\\Sm>>| (|<PPo1\\<PPs\\Sm>>__comp=1.deg| 上がる)
     (|<Sm\\Sm>| 。)))))
 (ID |13_BCCWJ-ABC-aa-simple|)))
		 (prej (car (find-nodes "comp=1\.prej" tree)))
		 (diff (car (find-nodes "comp=1\.diff" tree)))
		 (prej-relabeled
		  '(|<<<Sm\|PPs>\|DEG>\|<<<Sm\|PPs>\|<<PPs\\Sm>/<PPs\\Sm>>>\|<<PPs\\Sm>/<PPs\\Sm>>>>__comp=1.prej|
 (NP (N それ))
 (|<<<<Sm\|PPs>\|DEG>\|<<<Sm\|PPs>\|<<PPs\\Sm>/<PPs\\Sm>>>\|<<PPs\\Sm>/<PPs\\Sm>>>>\|NP>|
  より))
)
		 (transformed-tree-with-diff '(TOP
 (|Sm|
  (|<Sm/Sm>|
   (|<Sm/Sm>|
    (|Sa| (|PPs| (|NPq| (N 妻)) (|<NP\\PPs>| が))
     (|<PPs\\Sa>|
      (|<<PPs\\Sa>/<PPs\\Sa>>| (|NPq| (N 仕事))
       (|<NP\\<<PPs\\Sa>/<PPs\\Sa>>>| に))
      (|<PPs\\Sa>| 精出す)))
    (|<Sa\\<Sm/Sm>>| 一方))
   (|<<Sm/Sm>\\<Sm/Sm>>| 、))
  (|Sm__comp=1.cont.moved| (|PPs__comp=1.cont| (NP (N 赤沼)) (|<NP\\PPs>| は))
   (|<Sm\|PPs>__comp=1.diff.moved| (|DEG__comp=1.diff| もっと)
    (|<<Sm\|PPs>\|DEG>__comp=1.prej.moved|
     (|<<<Sm\|PPs>\|DEG>\|<<<Sm\|PPs>\|<<PPs\\Sm>/<PPs\\Sm>>>\|<<PPs\\Sm>/<PPs\\Sm>>>>__comp=1.prej|
      (NP (N それ))
      (|<<<<Sm\|PPs>\|DEG>\|<<<Sm\|PPs>\|<<PPs\\Sm>/<PPs\\Sm>>>\|<<PPs\\Sm>/<PPs\\Sm>>>>\|NP>|
       より))
     (|<<<Sm\|PPs>\|<<PPs\\Sm>/<PPs\\Sm>>>\|<<PPs\\Sm>/<PPs\\Sm>>>__comp=1.diff.bind|
      (|<<Sm\|PPs>\|<<PPs\\Sm>/<PPs\\Sm>>>__comp=1.prej.bind|
       (|<Sm\|PPs>__comp=1.cont.bind|
        (|Sm__comp=1.root+| (|PPs__comp=1.cont| |*TRACE-cont1*|)
         (|<PPs\\Sm>| (|<<PPs\\Sm>/<PPs\\Sm>>__comp=1.prej| |*TRACE-prej1*|)
          (|<PPs\\Sm>| (|<<PPs\\Sm>/<PPs\\Sm>>__comp=1.diff| |*TRACE-diff1*|)
           (|<PPs\\Sm>| (|<PPs\\Sm>__comp=1.deg| 忙しい) (|<Sm\\Sm>| 。))))))))))))
 (ID |5_BCCWJ-ABC-aa-simple|))
)
		 (transformed-tree-no-diff '(TOP
 (|Sm__comp=1.cont.moved|
  (|PPs__comp=1.cont| (|NPq| (N (<N/N> (NP (N 矛)) (|<NP\\<N/N>>| の)) (N 方)))
   (|<NP\\PPs>| が))
  (|<Sm\|PPs>__comp=1.prej.moved|
   (|<<Sm\|PPs>\|<<Sm\|PPs>\|<Sm/Sm>>>__comp=1.prej|
    (|NPq| (<NP/NP> (N 剣) (|<N\\<NP/NP>>| や)) (|NPq| (N 刀)))
    (|<<<Sm\|PPs>\|<<Sm\|PPs>\|<Sm/Sm>>>\|NPq>| (|<NP\\<Sm/Sm>>| より)
     (|<<Sm/Sm>\\<Sm/Sm>>| も)))
   (|<<Sm\|PPs>\|<Sm/Sm>>__comp=1.prej.bind|
    (|<Sm\|PPs>__comp=1.cont.bind|
     (|Sm__comp=1.root+| (|<Sm/Sm>__comp=1.prej| |*TRACE-prej1*|)
      (|Sm| (|PPs__comp=1.cont| |*TRACE-cont1*|)
       (|<PPs\\Sm>| (|PPo1| (NP (N 武威)) (|<NP\\PPo1>| が))
        (|<PPo1\\<PPs\\Sm>>| (|<PPo1\\<PPs\\Sm>>__comp=1.deg| 上がる)
         (|<Sm\\Sm>| 。)))))))))
 (ID |13_BCCWJ-ABC-aa-simple|))

)
		 )
	    (5am:is (equal '(|<<PPs\\Sm>/<PPs\\Sm>>__comp=1.prej| (NP (N それ))
			     (|<NP\\<<PPs\\Sm>/<PPs\\Sm>>>| より))
			   prej))
	    (5am:is (equal '(|<<PPs\\Sm>/<PPs\\Sm>>__comp=1.diff| もっと) diff))
	    (5am:is (equal prej-relabeled (relabel-prej-with-diff prej diff "<Sm|PPs>" "__comp=1.prej")))
	    (5am:is (equal transformed-tree-with-diff (sb-cltl2:macroexpand-all tree)))
	    (5am:is (equal transformed-tree-no-diff (sb-cltl2:macroexpand-all tree-no-diff)))

	    (5am:is (equal '(|<<PPs\\Sm>/<PPs\\Sm>>__comp=1.diff| |*TRACE-diff1*|)
			   (make-trace "<<PPs\\Sm>/<PPs\\Sm>>" "diff")))
	    
	    (5am:is (equal "diff" (cadr (cl-ppcre:split "\\." (get-suffix diff)))))
	    (5am:is (equal "comp=1.diff" (get-suffix diff)))
	    (5am:is (equal "<Sm|PPs>" (reduce #'vs (clist "PPs" (cat nil)) :initial-value "Sm")))
	    (5am:is (equal "Sm" (reduce #'vs () :initial-value "Sm")))
	    (5am:is (equal nil (treep '(a (b)))))
	    (5am:is (equal t (treep  '(b c))))
	    (5am:is (equal t (treep '(a (b c)))))
	    (5am:is (equal nil (treep '(a (b (c)) (d (e f))))))

	    (5am:is (equal "prej" (filler-type '(|<<PPs\\Sm>/<PPs\\Sm>>__comp=1.prej__deriv=<| (|NP__deriv=unary-unknown| (N それ)) (|<NP\\<<PPs\\Sm>/<PPs\\Sm>>>| より)))))
	    
	    ))


;; ;; ;; for testing
;; (defparameter *debug-on-failure* t)
;; (5am:run!)


(defvar trees-new)


;;読み込んだツリーをmacroexpandして書き出す

(setq trees-new (mapcar #'(lambda (x) (remove-if-not #'treep (sb-cltl2:macroexpand-all x))) trees))
(mapc #'(lambda (x) (princ x)) trees-new)


