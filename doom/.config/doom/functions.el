;;; ~/.doom.d/functions.el -*- lexical-binding: t; -*-

(defun delete-surrounding-whitespace ()
  (interactive)
  (let ((skip-chars "\t\n\r "))
    (skip-chars-backward skip-chars)
    (let* ((start (point))
           (num (progn
                  (skip-chars-forward skip-chars)
                  (point))))
      (delete-region start num))))

(defun lotto-cljs ()
  (interactive)
  (cider-connect-cljs '(:host "localhost" :port 9001 :cljs-repl-type shadow)))

(defun copy-buffer-filename-to-clipboard ()
  (interactive)
  (kill-new (buffer-file-name)))

(defun httpsify (url)
  (if (string-prefix-p "git@" url)
      (replace-regexp-in-string
       ".com:"
       ".com/"
       (replace-regexp-in-string "git@" "https://" url))
    url))

(defun clipboard-github-link-from-current-line ()
  (interactive)
  (let* ((base-url (httpsify (substring (magit-get "remote" "origin" "url") 0 -4)))
         (project-file-name (replace-regexp-in-string
                             (counsel-locate-git-root)
                             ""
                             (buffer-file-name)))
         (url-format "%s/blob/%s/%s#L%s"))
    (kill-new (format url-format base-url (magit-get-current-branch) project-file-name (line-number-at-pos)))))

(defun clipboard-man7 (manpage)
  (interactive "sCopy to clipboard manpage link for: ")
  (cl-destructuring-bind (manpage word) (split-string manpage)
    (kill-new (format "https://man7.org/linux/man-pages/man%s/%s.%s.html" manpage word manpage))))

(defun calculate-dpi ()
  (let ((width-in-inches (/ (x-display-mm-width) 25.4))
        (height-in-inches (/ (x-display-mm-height) 25.4))
        (width-in-pixels (display-pixel-width))
        (height-in-pixels (display-pixel-height)))
    (let ((width-dpi (/ width-in-pixels width-in-inches))
          (height-dpi (/ height-in-pixels height-in-inches)))
      (list width-dpi height-dpi))))

(defun shell-escape-string (str)
  "Escape shell metacharacters in STR."
  (replace-regexp-in-string
   "\\([\\$\"'` \t\n*?#(){};<>|&![]\]\\)" "\\\\\\1" str))

(defun shell-command-on-fileized-region (command)
  "Creates a temporary file using the text of the selection region.
Passes that file to the specified shell command, as its first
argument. Replaces the selected region with the output of the
shell command."
  (interactive)
  (replace-region-contents
   (region-beginning)
   (region-end)
   (lambda ()
     (let ((file (make-temp-file "black-"))
           (contents (buffer-substring (point-min) (point-max))))
       (with-temp-file file
         (insert contents))
       (shell-command (format "%s %s" command (cl-coerce file 'string)))
       (with-temp-buffer
         (insert-file-contents file)
         (buffer-string))))))

(defun racket-eval-last-sexp-and-comment ()
  "Eval the expression before point asynchronously.
The result is inserted as a comment on the next line.
The expression may be either an at-expression or an s-expression."
  (interactive)
  (racket--assert-sexp-edit-mode)
  (unless (racket--repl-session-id)
    (user-error "No REPL session available; run the file first"))
  (let ((beg (racket--start-of-previous-expression))
        (end (point)))
    (racket--cmd/async
     (racket--repl-session-id)
     `(eval ,(buffer-substring-no-properties beg end))
     (lambda (v)
       (save-excursion
         (end-of-line)
         (newline-and-indent)
         (insert (format ";; => %s" v)))))))
