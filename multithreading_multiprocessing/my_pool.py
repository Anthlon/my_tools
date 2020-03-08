"""
Write a Pool implementation with the following requirements:
---
 * Number of processes in the Pool should be configurable
 * Pool has `map` method which accepts mapping function and iterable to be mapped
 * `Pool.map` returns ordered results
 * Pool splits iterable evenly between processes, items from iterable should be passed to processes 1 by 1
 * Processes should start when pool was created, not when `map` was called
 * You can use only 1 Pipe (can be duplex)
 * Pool.map can be called as many times as user wants

Provide a solution with demonstration code: factorial calculation

Bonus task:
---
If you want more challenge, add `max_process_tasks` parameter to the Pool.
Each process in the pool can process only `max_process_tasks` number of tasks and then should be destroyed,
then Pool should create new processes and add them to the pool up to a pool size.
Pool now can use new process to complete its tasks.
"""
import sys
import time
from multiprocessing import Process, Lock, Pipe


class DeadSignal(Exception):
    pass


def _call_back_from_manager(pipe):
    time.sleep(0.05)
    if pipe.poll():
        index, function_args = pipe.recv()
        return index, function_args
    raise DeadSignal('Worker dead')


def push_response_and_get_request(pipe, lock, *response):
    lock.acquire()
    if response[0] is None:
        pipe.send(True)
    else:
        pipe.send(response)
    try:
        return _call_back_from_manager(pipe)
    finally:
        lock.release()


def concurrent_process(pipe, lock, function):
    index, result = None, None
    while not pipe.closed:
        try:
            index, function_args = push_response_and_get_request(pipe, lock, index, result)
        except DeadSignal:
            break
        else:
            result = function(function_args)


class MyPool:
    def __init__(self, process_count=1):
        self.process_count = process_count

    def _create_workers(self, function, function_args, remote_pipe, lock):
        workers = list()
        for number_worker in range(min(self.process_count, len(function_args))):
            worker = Process(target=concurrent_process, args=(remote_pipe, lock, function))
            worker.start()
            workers.append(worker)
        return workers

    def map(self, function, *function_args):
        lock = Lock()
        main_pipe, remote_pipe = Pipe()
        requests = list(enumerate(function_args))
        works_count = len(function_args)
        results = [self] * works_count
        workers = self._create_workers(function, function_args, remote_pipe, lock)

        cursor = 0
        while cursor < works_count:
            if results[cursor] is not self:
                yield results[cursor]
                cursor += 1
            if main_pipe.poll():
                response = main_pipe.recv()
                if requests:
                    main_pipe.send(requests.pop(0))
                if response is not True:
                    index, result = response
                    results[index] = result

        for worker in workers:
            worker.join()
        main_pipe.close()
        raise StopIteration


if __name__ == '__main__':

    def sleeper(t):
        time.sleep(t*2)
        return t

    args = range(1, 10)
    mp = MyPool(4)
    for i in mp.map(sleeper, *args):
        print(i, end=' ')
        sys.stdout.flush()
    print()

    import requests as rq
    import os

    POP20_CC = 'CN IN US ID BR PK NG BD RU JP MX PH VN ET EG DE IR TR CD FR'.split()
    BASE_URL = 'http://flupy.org/data/flags'
    DOWNLOAD_DIR = 'downloads/'

    def download_flag(short_flag_name):
        image = rq.get(f'{BASE_URL}/{short_flag_name.lower()}/{short_flag_name.lower()}.gif').content
        with open(os.path.join(DOWNLOAD_DIR, f'{short_flag_name}.gif'), 'wb') as fp:
            fp.write(image)
        return short_flag_name

    if not os.path.exists(DOWNLOAD_DIR):
        os.mkdir(DOWNLOAD_DIR)

    for i in mp.map(download_flag, *POP20_CC):
        print(i, end=' ')
        sys.stdout.flush()
    print()
