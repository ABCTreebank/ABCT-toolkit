FROM python:3.6.12-buster
ARG USERNAME=vscode
ARG USER_UID=1000

ENV LANG C.UTF-8

RUN useradd --create-home \
    --shell /bin/bash \
    --uid ${USER_UID} \
    --user-group \
    ${USERNAME}

RUN apt update \
    && apt install -y less default-jre m4 \
    && apt clean
    
RUN curl -sSL https://get.haskellstack.org/ | sh

USER ${USERNAME}
ENV PATH /home/${USERNAME}/.local/bin:${PATH}

RUN pip install pipx && pipx ensurepath && pipx install poetry 