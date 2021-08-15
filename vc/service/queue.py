import json
from flask_rq import get_queue, get_connection
from injector import Binder, inject
from rq import Queue, Worker


class JobSerializer:
    binder: Binder

    @inject
    def __init__(self, binder: Binder):
        self.binder = binder

    def dumps(self, *args, **kwargs):
        [method, _, fnargs, fnkwargs] = args[0]
        [class_name, method] = method.rsplit('.', 1)
        return json.dumps([
            method,
            class_name,
            fnargs,
            fnkwargs
        ], **kwargs).encode('utf-8')

    def loads(self, s, *args, **kwargs):
        [method, class_name, fnargs, fnkwargs] = json.loads(
            s.decode('utf-8'),
            *args,
            **kwargs
        )

        class_instance = self.binder.injector.get(
            self.handle_import(class_name)
        )

        return [
            method,
            class_instance,
            fnargs,
            fnkwargs
        ]

    # @see https://stackoverflow.com/questions/547829/how-to-dynamically-load-a-python-class
    def handle_import(self, name):
        components = name.split('.')
        mod = __import__(components[0])
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod


class QueueService:
    TIMEOUT = 600

    job_serializer: JobSerializer
    queue: Queue = None
    worker: Worker = None

    @inject
    def __init__(self, job_serializer: JobSerializer):
        self.job_serializer = job_serializer

    def enqueue(self, f, args=None, kwargs=None):
        self.get_queue().enqueue_call(
            f,
            args=args,
            kwargs=kwargs,
            timeout=self.TIMEOUT
        )

    def get_worker(self):
        if self.worker is None:
            queue = self.get_queue()
            self.worker = Worker(
                [queue],
                connection=get_connection(queue.name),
                serializer=self.job_serializer
            )
        return self.worker

    def get_queue(self):
        if self.queue is None:
            self.queue = get_queue(serializer=self.job_serializer)
        return self.queue