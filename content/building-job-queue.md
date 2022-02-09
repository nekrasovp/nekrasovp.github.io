Title: Building job queue
Author: Nekrasov Pavel
Date: 2021-10-01 15:00
Category: Blog
Tags: python, rabbitmq
Slug: building-job-queue
Summary: In this article, we will build simple job queue on top of rabbitmq-server with aio-pika package.

## Abstract

Whether your application is in the cloud or in your own data center, RabbitMQ is a lightweight and extremely powerful tool for creating distributed software architectures that range from the very simple to the incredibly complex.

In this article, we will build simple job queue on top of rabbitmq-server with aio-pika package.

## Contents

- [Abstract](#abstract)
- [Contents](#contents)
- [Install pre-requisite packages](#install-pre-requisite-packages)
  - [Run RabitMQ community docker image](#run-rabitmq-community-docker-image)
  - [Activate virtual environment and install dependencies](#activate-virtual-environment-and-install-dependencies)
- [Prepare shared function](#prepare-shared-function)
- [Create asyncronious worker](#create-asyncronious-worker)
- [Create job queue and run shared function](#create-job-queue-and-run-shared-function)
- [Run it](#run-it)

## Install pre-requisite packages

### Run RabitMQ community docker image

```sh
docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.9-management
```

### Activate virtual environment and install dependencies

```sh
python -m venv venv
source venv/bin/activate
python -m pip install aio-pika
```

## Prepare shared function

In this example we will use simple shared function:

```python
from time import sleep

def simple_func(text: str):
    sleep(1)
    print(f"Good morning {text}")
```

## Create asyncronious worker

```python
import asyncio
import pickle

from aio_pika import connect, IncomingMessage


loop = asyncio.get_event_loop()


def wrapper(pickled_fn):
    [func, args] = pickle.loads(pickled_fn)
    func(args)


async def on_message(message: IncomingMessage):
    wrapper(message.body)
    message.ack()


async def main():
    # Perform connection
    connection = await connect("amqp://guest:guest@localhost/", loop=loop)

    # Creating a channel
    channel = await connection.channel()
    await channel.set_qos()

    # Declaring queue
    queue = await channel.declare_queue(
        "task_queue",
        durable=True
    )

    # Start listening the queue with name 'task_queue'
    await queue.consume(on_message)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())

    # we enter a never-ending loop that waits for data and runs
    # callbacks whenever necessary.
    print(" Waiting for messages. To exit press CTRL+C")
    loop.run_forever()
```

## Create job queue and run shared function

```python
import asyncio
import pickle

from aio_pika import connect, Message, DeliveryMode

from shared import simple_func


async def submit_helper(func, args, loop):
    # Perform connection
    connection = await connect("amqp://guest:guest@localhost/", loop=loop)

    # Creating a channel
    channel = await connection.channel()

    message_body = pickle.dumps([func, args]) 
    message = Message(
        message_body,
        delivery_mode=DeliveryMode.PERSISTENT
    )

    # Sending the message
    await channel.default_exchange.publish(
        message, routing_key="task_queue"
    )

    await connection.close()


def submit_job(func, args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(submit_helper(func, args, loop))


if __name__ == '__main__':
    submit_job(simple_func, 'world')
```

## Run it

We will need to open 3 terminals to notice all executions

1. Run docker container with RabitMQ

2. Run  async worker

```sh
python worker_async.py
```

3. Run job queue and call our shared function

```sh
python job_queue.py
```

Finally you have to get something like this in your terminals

![sio-pika-example](images/aio-pika-example.png)