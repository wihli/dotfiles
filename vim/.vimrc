" Enable syntax highlighting
syntax enable
syntax on

" Enable file type detection and plugin/indent loading
filetype plugin indent on

" Set a good default colorscheme
colorscheme desert

" Basic settings for better experience
set background=dark
set number
set relativenumber
set ruler
set laststatus=2
set showcmd
set showmode

" Search settings
set hlsearch
set incsearch
set ignorecase
set smartcase

" Indentation
set autoindent
set smartindent
set expandtab
set tabstop=4
set shiftwidth=4
set softtabstop=4

" Better colors for dark terminals
if &term =~ '256color'
  set t_Co=256
endif

" Enable mouse support
set mouse=a

" Show matching brackets
set showmatch

" Better command-line completion
set wildmenu
set wildmode=longest:full,full

" Disable swap files
set noswapfile
set nobackup
set nowritebackup

" Better split defaults
set splitbelow
set splitright

" Always use UTF-8
set encoding=utf-8
set fileencoding=utf-8

" Highlight current line
set cursorline

" Show whitespace characters
set list
set listchars=tab:▸\ ,trail:·,extends:❯,precedes:❮

" Better backspace behavior
set backspace=indent,eol,start

" Faster redrawing
set ttyfast

" Don't redraw while executing macros
set lazyredraw

" Keep some context when scrolling
set scrolloff=5
set sidescrolloff=5