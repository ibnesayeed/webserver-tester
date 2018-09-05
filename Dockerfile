FROM    python
LABEL   maintainer="Sawood Alam <@ibnesayeed>"

WORKDIR /app
COPY    requirements.txt ./
RUN     pip install -r requirements.txt
COPY    . ./
RUN     chmod a+x server.py

CMD     ["./server.py"]
