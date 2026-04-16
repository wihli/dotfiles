;;; ~/.doom.d/bindings.el -*- lexical-binding: t; -*-

(map! :leader
      "lh" #'scroll-left
      "ll" #'scroll-right
      "ow" #'treemacs-select-window
      "cg" #'clipboard-github-link-from-current-line
      "cm" #'clipboard-man7
)

(map!
 :ni "C-S-d" #'delete-surrounding-whitespace
 :nm  "C-S-o" #'better-jumper-jump-forward)

(map! (:map clojure-mode-map
       :localleader
       :n "s" #'lotto-cljs))

(map! (:map racket-mode-map
       :localleader
       :n "c" #'racket-eval-last-sexp-and-comment))
