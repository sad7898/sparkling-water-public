FROM --platform=linux/amd64 public.ecr.aws/amazonlinux/amazonlinux:2023-minimal AS base

RUN dnf install -y gcc python3 python3-devel

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt

RUN python3 -m pip install --upgrade pip && \
    pip3 install -r /tmp/requirements.txt && \
    pip3 install torch --index-url https://download.pytorch.org/whl/cpu && \
    python3 -m pip install venv-pack==0.2.0

RUN mkdir /output && venv-pack -o /output/pyspark_venv.tar.gz

CMD ["bash"]
