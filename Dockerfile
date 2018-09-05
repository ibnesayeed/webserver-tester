FROM    python
LABEL   maintainer="Sawood Alam <@ibnesayeed>"

RUN     apt update && apt install -y netcat \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY    requirements.txt ./
RUN     pip install -r requirements.txt
COPY    . ./
RUN     chmod a+x *.py

CMD     ["./server.py"]
