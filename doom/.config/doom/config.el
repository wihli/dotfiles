;;; $DOOMDIR/config.el -*- lexical-binding: t; -*-

;; Place your private configuration here! Remember, you do not need to run 'doom
;; sync' after modifying this file!

;; Fish is non-POSIX; Emacs internals (TRAMP, diff-hl, shell-command) break
;; when $SHELL is fish. Use bash internally, keep fish for interactive terminals.
(setq shell-file-name (executable-find "bash"))
(setq-default vterm-shell (executable-find "fish"))
(setq-default explicit-shell-file-name (executable-find "fish"))

;; Prevent TRAMP hangs: disable expensive remote operations
(after! tramp
  (setq tramp-default-method "ssh")
  ;; Simpler prompt regexp avoids shell detection hangs
  (setq tramp-shell-prompt-pattern "\\(?:^\\|\r\\)[^]#$%>\n]*#?[]#$%>].* *\\(^[\\[[0-9;]*[a-zA-Z] *\\)*"))

;; Disable vc, lsp, and file watchers for remote buffers
(defun remote--disable-expensive-modes ()
  "Turn off modes that hang over TRAMP."
  (when (file-remote-p default-directory)
    (setq-local vc-handled-backends nil)
    (when (bound-and-true-p lsp-mode) (lsp-disconnect))
    (when (bound-and-true-p flycheck-mode) (flycheck-mode -1))))

(add-hook 'find-file-hook #'remote--disable-expensive-modes)
(add-hook 'dired-mode-hook #'remote--disable-expensive-modes)

;; Projectile: use caching for remote projects
(after! projectile
  (setq projectile-enable-caching t))

;; Treemacs: don't poll remote filesystems
(after! treemacs
  (setq treemacs-file-event-delay 5000)
  (treemacs-git-mode -1))

;; Some functionality uses this to identify you, e.g. GPG configuration, email
;; clients, file templates and snippets.
(setq user-full-name "Eric Ihli"
      user-mail-address "eric.ihli@vanta.com")

;; Doom exposes five (optional) variables for controlling fonts in Doom. Here
;; are the three important ones:
;;
;; + `doom-font'
;; + `doom-variable-pitch-font'
;; + `doom-big-font' -- used for `doom-big-font-mode'; use this for
;;   presentations or streaming.
;;
;; They all accept either a font-spec, font string ("Input Mono-12"), or xlfd
;; font string. You generally only need these two:
;; 24 for hidpi
;; 12 for lodpi
(setq doom-font (font-spec :family "Menlo" :size 18))
(setq doom-symbol-font (font-spec :family "Symbols Nerd Font Mono" :size 18))

;; There are two ways to load a theme. Both assume the theme is installed and
;; available. You can either set `doom-theme' or manually load a theme with the
;; `load-theme' function. This is the default:
(setq doom-theme 'doom-one)

;; If you use `org' and don't want your org files in the default location below,
;; change `org-directory'. It must be set before org loads!
(setq org-directory "~/org/")

;; This determines the style of line numbers in effect. If set to `nil', line
;; numbers are disabled. For relative line numbers, set this to `relative'.
(setq display-line-numbers-type t)


;; Here are some additional functions/macros that could help you configure Doom:
;;
;; - `load!' for loading external *.el files relative to this one
;; - `use-package' for configuring packages
;; - `after!' for running code after a package has loaded
;; - `add-load-path!' for adding directories to the `load-path', relative to
;;   this file. Emacs searches the `load-path' when you load packages with
;;   `require' or `use-package'.
;; - `map!' for binding new keys
;;
;; To get information about any of these functions/macros, move the cursor over
;; the highlighted symbol at press 'K' (non-evil users must press 'C-c g k').
;; This will open documentation for it, including demos of how they are used.
;;
;; You can also try 'gd' (or 'C-c g d') to jump to their definition and see how
;; they are implemented.

(use-package! adoc-mode
  :mode ("\\.adoc\\'" . adoc-mode))

(use-package! stumpwm-mode)
(use-package! smart-tabs-mode
  :config
  (autoload 'smart-tabs-mode "smart-tabs-mode")
  (autoload 'smart-tabs-mode-enable "smart-tabs-mode")
  (autoload 'smart-tabs-advice "smart-tabs-mode")
  (autoload 'smart-tabs-insinuate "smart-tabs-mode"))

(use-package! flycheck-clj-kondo)

(use-package! extempore-mode
  :config
  (paredit-mode))

; I think this was causing an issue with C-c '
(use-package! poly-org)

(use-package! clojure-mode
  :config
  (require 'flycheck-clj-kondo)
  (require 'ob-clojure)
  (setq cider-clojure-cli-parameters "-A:cider-nrepl"
        cider-required-middleware-version "0.52.0"
        cider-jack-in-auto-inject-clojure nil
        cider-jack-in-lein-plugins nil
        org-babel-clojure-backend 'cider))

;; (use-package! geiser
;;   :config
;;   (setq geiser-active-implementations '(chez))
;;   (setq geiser-chez-binary "chez")
;;   (setq geiser-chez--prompt-regexp ".*>.*"))

(use-package! paredit)

(after! js-mode
  (setq js-indent-level 2))

(use-package! web-mode
  :mode ("\\.html\\'" . web-mode)
  :config
  (setq-default tab-width 2)
  (web-mode-use-tabs)
  (emmet-mode)
  (setq-default electric-indent-mode nil))

(use-package! hcl-mode
  :mode (("\\.hcl\\.j2\\'" . hcl-mode)
         ("\\.hcl\\'" . hcl-mode)))

(use-package! seq
  :ensure t)

(use-package! clj-refactor
  :hook (clojure-mode . clj-refactor-mode)
  :config
  (set-lookup-handlers! 'clj-refactor-mode
    :references #'cljr-find-usages)
  (map! :map clojure-mode-map
        :localleader
        :desc "refactor" "R" #'hydra-cljr-help-menu/body))

;; https://github.com/doomemacs/doomemacs/issues/6317
(after! poetry
  (remove-hook 'python-mode-hook #'poetry-tracking-mode)
  (add-hook 'python-mode-hook 'poetry-track-virtualenv))

(after! clojure
  (define-clojure-indent
    (>defn :defn)
    (defsc :defn)
    (action :defn)
    (defmutation :defn)))

;; (add-hook! (racket-mode)
;;            '(paredit-mode))

(add-hook! (clojure-mode lisp-mode)
           '(paredit-mode (lambda () (require 'flycheck-clj-kondo)))
           (setq tab-width 8))

(add-hook 'emacs-lisp-mode-hook 'paredit-mode)

(use-package! lit-mode)

(use-package! tide)
(defun setup-tide-mode ()
  (interactive)
  (tide-setup)
  (flycheck-mode +1)
  (setq flycheck-check-syntax-automatically '(save mode-enabled))
  (setq flycheck-checker 'javascript-eslint)
  (setq tab-width 4)
  (eldoc-mode +1)
  (tide-hl-identifier-mode +1)
  ;; company is an optional dependency. You have to
  ;; install it separately via package-install
  ;; `M-x package-install [ret] company`
  (company-mode +1))

;; aligns annotation to the right hand side
(setq company-tooltip-align-annotations t)

;; formats the buffer before saving
(add-hook 'before-save-hook 'tide-format-before-save)
(add-hook 'typescript-mode-hook #'setup-tide-mode)

(use-package! json-mode)
(use-package! gptel)

(setq sly-complete-symbol-function 'sly-flex-completions)

(setq-default truncate-lines nil)


(map!
 :map rst-mode-map
 :leader
 (:prefix "r"
  :n
  "t" #'rst-toc
  "s" #'rst-toc-follow-link))

(add-to-list 'exec-path "/home/eihli/.local/bin")

(org-babel-do-load-languages
 'org-babel-load-languages
 '((python . t)
   (emacs-lisp . nil)
   (sql . t)))

(add-to-list 'flycheck-disabled-checkers 'python-pylint)
(defun ow-fundamental-mode-setup ()
  (setq tab-always-indent t)
  (setq indent-tabs-mode t)
  (setq indent-line-function 'insert-tab)
  (local-set-key (kbd "TAB") 'tab-to-tab-stop)
  (local-set-key (kbd "RET") 'newline))

(add-hook 'fundamental-mode-hook 'ow-fundamental-mode-setup)

;; This is specifically because PyTorch has several dozen sub-module git repos and it really slows down lsp.
(add-hook 'lsp-mode-hook
          (lambda ()
            (add-to-list 'lsp-file-watch-ignored-directories "[/\\\\]third_party\\'")
            (setq lsp-file-watch-threshold 1500)))

(setq lsp-file-watch-ignored
      '("/logs" ;; SWE-Bench
        "/.git"
        "/.venv"
        "/retrieval_results" ;; SWE-Bench
        "/test_splade_output" ;; SWE-Bench
        ))

(setq lsp-enable-file-watchers nil)

(use-package! pet
  :config
  (add-hook 'python-mode-hook
            (lambda ()
              (setq-local python-shell-interpreter (pet-executable-find "python")
                          python-shell-virtualenv-root (pet-virtualenv-root))
              (pet-flycheck-setup)
              (pet-eglot-setup))))
(after! projectile
  (add-to-list 'projectile-globally-ignored-directories "target/")
  (add-to-list 'projectile-globally-ignored-directories ".exercism/"))


(load! "functions")
(load! "bindings")

(server-start)

