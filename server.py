#!/usr/bin/env python3

import sys
import socket
import datetime
import json
import queue
import threading
import subprocess
import pathlib
import io
from ollama import Client, Message

DOWNLOOAD_LIST = queue.Queue()


# Block size is set to 8192 because thats usually the max header size
BLOCK_SIZE = 8192


def serve(host='0.0.0.0', port=3246, verbosity=1):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(1)

        if verbosity > 0:
            print('Echoing from http://{}:{}'.format(host, port))

        while True:
            connection, client_address = sock.accept()

            request = {}
            bytes_left = BLOCK_SIZE
            while bytes_left > 0:
                if bytes_left > BLOCK_SIZE:
                    data = connection.recv(BLOCK_SIZE)
                else:
                    data = connection.recv(max(0, bytes_left))

                if not 'header' in request:
                    request = build_request(data)
                    header_length = len(request['raw']) - len(request['body'])
                    body_length_read = BLOCK_SIZE - header_length
                    if 'content-length' in request['header']:
                        bytes_left = int(
                            request['header']['content-length']) - body_length_read
                    else:
                        bytes_left = 0
                else:
                    request['raw'] += data
                    request['body'] += data.decode('utf-8', 'ignore')
                    bytes_left -= BLOCK_SIZE

            request_time = datetime.datetime.now().ctime()

            if verbosity > 0:
                print(
                    ' - '.join([client_address[0], request_time, request['header']['request-line']]))

            raw_decoded = request['raw'].decode('utf-8', 'ignore')
            try:
                data = json.loads(request['body'])
                fname = pathlib.Path(data["path"])
                summary = pathlib.Path('summaries/' + fname.name + '.txt')
                error = pathlib.Path('errors/' + fname.name + '.txt')
                if summary.exists():
                    html = subprocess.run(["pandoc", "-f", "markdown", "-t", "html", str(summary)],
                                          capture_output=True).stdout.decode('utf-8', errors='ignore')

                    raw_decoded = json.dumps(
                        {"summary": html}, ensure_ascii=False)
                elif error.exists():
                    raw_decoded = json.dumps(
                        {"error": error.read_text()}, ensure_ascii=False)
                else:
                    DOWNLOOAD_LIST.put(data)
                    raw_decoded = json.dumps(
                        {"downloading": True}, ensure_ascii=False)
            except Exception as e:
                print(e)
            response = "HTTP/1.1 200 OK\nAccess-Control-Allow-Origin: *\nContent-Type: application/json; charset=utf-8\n\n{}".format(
                raw_decoded)
            if verbosity == 2:
                print("-"*10)
                print(response)
                print("-"*40)
            connection.sendall(response.encode())
            connection.close()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        sock.close()


def build_request(first_chunk):
    lines = first_chunk.decode('utf-8', 'ignore').split('\r\n')
    h = {'request-line': lines[0]}
    i = 1
    while i < len(lines[1:]) and lines[i] != '':
        k, v = lines[i].split(': ')
        h.update({k.lower(): v})
        i += 1
    r = {
        "header": h,
        "raw": first_chunk,
        "body": lines[-1]
    }
    return r


def make_summary(data):
    fname = pathlib.Path(data["path"])
    if pathlib.Path('summaries/' + fname.name + '.txt').exists():
        print(f"{str(fname)[-80:]:>80.80}: summary exists, skipping ...",
              end="\n", flush=True)
        return
    txt = ""
    if pathlib.Path('txts/' + fname.name + '.txt').exists():
        txt = pathlib.Path('txts/' + fname.name + '.txt').read_text()
    if len(txt) <= 1000:
        print(f"{str(fname)[-80:]:>80.80}: extracting text ...",
              end="\r", flush=True)
        txt = subprocess.run(["pdftotext", data["path"], "-"],
                             capture_output=True).stdout.decode('utf-8', errors='ignore')
        if len(txt) > 1000:
            io.open('txts/' + fname.name + '.txt',
                    'w').write(txt)
        else:
            print(f"{str(fname)[-80:]:>80.80}: text-extraction too short. Corrupt file?\nExtracted: {txt}",
                  end="\n", flush=True, file=sys.stderr)
            with pathlib.Path('errors/' + fname.name + '.txt').open(mode='w') as errfile:
                print(
                    "text-extraction too short. Corrupt file?\nExtracted: {txt}", file=errfile)
            return
    print(f"{str(fname)[-80:]:>80.80}: waiting for response ...",
          end="\r", flush=True)
    tagger = Client(host="http://172.28.105.78:11434")
    tagged = tagger.chat(
        model="phi3:14b-medium-128k-instruct-f16",
        messages=[{"role": "user",
                   "content": txt},
                  {"role": "system",
                   "content": """You just got a text in a very rough textual format. It contains a lot of unnecessary tokens.

Use one of these template and continue rewriting and filling out the missing bits - and leave hints for yourself like `[more information necessary]` or `[not yet presented]` as placeholder and hints on what to do here as long as you get fed more content. Being correct is more important than completely filling each section of the template. You will get the opportunity to fill in gaps later, but you will get punished severely for each error that is being detected by human oversight.
The target audience is a knowledgable researcher, so you do not need to explain anything, just give a brief but precise overview.

If you can not find any scientific methodology assume that you were not given a scientific paper and the template makes no real sense. In this case use the generic template.

Whatever you chose, always make sure, that
- you do not make up any new markdown-style headings or change the structure of the template. The chosen template needs to be formatted in exactly this way for downstream processing.
- before outputting the template give your reasoning for chosing such template based on a short content-proof as comment `<!-- Template x filled out because [reasons] -->` on the first line.

## **generic** Template: ##

When to use:
- there is no scientific approach or experiments in the supplied document
- the structure of your given text is a distinctly different to what is expected for the other templates
- the given text is a form of
    - legal document
    - written by an official entity (lawyer, city council, ...)
    - diary entry
    - other text of contemporary history

```markdown
<!-- Template x filled out because [reasons] -->
# [Title of the text]

## Short summary
[not yet presented] [2 to 3 paragraphs; more, if neccessary; use bullet-points if it makes sense]

[append the following always verbatim and end with "---"]
## Note
This summary was automagically generated using a good™ prompt on microsofts phi3:14b-medium-128k-f16 LLM.

---
```

## **scientific** Template: ##

When to use:
- you get a modern scientific paper

```markdown
<!-- Template x filled out because [reasons] -->
# [Title of the paper]

## Short summary
[not yet presented] [at most 5 sentences]

## Methodology
[must be present. Don't use this template in this case] [As few sentences as necessary, but without removing important details]

## Results

### Main takeaway
[not yet presented]

### Strengths
[not yet presented]

### Weaknesses
[not yet presented]

### Open questions
[not yet presented]


[append the following always verbatim and end with "---"]
## Note
This summary was automagically generated using a good™ prompt on microsofts phi3:14b-medium-128k-f16 LLM.

---
```

"""}
                  ],
        options={
            "temperature": 0.001,
            "repeat_penalty": 1.0,
            "seed": 42,
            "num_ctx": 128000,
            "top_p": 0.9},
        stream=True,
    )
    i = 0
    response: list[str] = []
    lastline: str = ""
    for x in tagged:
        rstring: str = str(x["message"]["content"]
                           if x["message"] is not None else "")

        response += [rstring]
        lastline = lastline + rstring
        preview = lastline.replace('\n', '')[-150:]
        print(f"{str(fname)[-80:]:>80.80}: {preview:<150}",
              end="\r", flush=True)
        i += len(rstring)
        if i > 150:
            # print("\r\033[2K", end="", flush=True)
            i = 0
        if '\n' in lastline:
            print("")
            if lastline.startswith("---\n"):
                break
            if "phi3:14b-medium-128k-f16 llm.\n" in lastline.lower():
                break
            lastline = lastline[lastline.rindex('\n')+1:]
        # if "---" in ''.join(response).splitlines() or "phi3:14b-medium-128k-f16" in ''.join(repsonse):
        #     break

    response = ''.join(response).strip()
    io.open('summaries/' + fname.name + '.txt',
            'w').write(response)
    print('summaries/' + fname.name + '.txt written..')


def download_thread():
    while True:
        try:
            next = DOWNLOOAD_LIST.get(True, 5)
            make_summary(next)
            # threading.Thread(target=make_summary, args=[next]).start()
        except queue.Empty:
            pass


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Server that returns any http request made to it")
    parser.add_argument('-b', '--bind', default='localhost',
                        help='host to bind to')
    parser.add_argument('-p', '--port', default=3246,
                        type=int, help='port to listen on')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='print all requests to terminal')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='silence all output (overrides --verbose)')
    args = parser.parse_args()
    host = args.bind
    port = args.port
    verbose = args.verbose
    quiet = args.quiet

    verbosity = 1
    if verbose:
        verbosity = 2
    if quiet:
        verbosity = 0

    threading.Thread(target=download_thread).start()
    serve(host, port, verbosity)
