FROM ubuntu:focal-20200729

# https://qiita.com/ay__1130/items/d36b0673de637b675db2
ARG DEBIAN_FRONTEND=noninteractive
ENV LANG C.UTF-8
ENV TZ Asia/Tokyo

# ------------
# Requirements
# ------------
RUN apt update \
    && apt install -y \
        make build-essential libssl-dev zlib1g-dev \
        libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
        libncurses5-dev libncursesw5-dev xz-utils tk-dev \ 
        automake libcurl4-openssl-dev \
        less default-jre m4 git \
        ruby 
# NOTE: keep caches for later usage

# ------------
# Python
# ------------
WORKDIR /tmp

# ref. https://realpython.com/installing-python/https://realpython.com/installing-python/
RUN curl https://www.python.org/ftp/python/3.9.12/Python-3.9.12.tgz \
    | tar zxf - \
    && cd Python-3.9.12 \
    && ./configure --enable-optimizations --with-ensurepip=install \
    && make -j 8 \
    && make altinstall \
    && cd .. && rm -rf Python-3.9.12

# ------------
# Haskell
# ------------
RUN curl -sSL https://get.haskellstack.org/ | sh

# ------------
# Roswell (Common Lisp)
# ------------
WORKDIR /tmp
RUN git clone -b release https://github.com/roswell/roswell.git roswell \
    && cd roswell \
    && sh bootstrap \
    && ./configure \
    && make \ 
    && make install \
    && cd .. && rm -rf roswell

# ------------
# munge-trees
# ------------
WORKDIR /tmp
RUN curl http://web.science.mq.edu.au/~mjohnson/code/munge-trees.tgz \
    | tar xzf - \
    && cd munge-trees \
    && make \ 
    && mv munge-trees /usr/local/bin \
    && cd .. && rm -rf munge-trees 

# ------------
# User settings
# ------------
ARG USERNAME=vscode
ARG USER_UID=1000
RUN useradd --create-home \
    --shell /bin/bash \
    --uid ${USER_UID} \
    --user-group \
    ${USERNAME}

USER ${USERNAME}
ENV PATH /home/${USERNAME}/.local/bin:${PATH}
WORKDIR /home/vscode

RUN python3.9 -m pip install --user pipx \
   && pipx ensurepath \
   && pipx install poetry

RUN git clone https://github.com/ABCTreebank/amoove /home/${USERNAME}/amoove \
    && ros init \
    && ros install fset fiveam trivia function-cache unix-opts \
    && ln -s /home/${USERNAME}/amoove /home/${USERNAME}/.roswell/local-projects/amoove