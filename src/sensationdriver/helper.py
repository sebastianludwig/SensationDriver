import asyncio
import traceback

def create_exception_reporting_task(coroutine, loop, logger):
    def report_exception(task):
        if task.exception():
            ex = task.exception()
            output = traceback.format_exception(ex.__class__, ex, ex.__traceback__)
            if logger is not None:
                logger.critical(''.join(output))

    # TODO use self._loop.create_task once Python 3.4.2 is released
    task = asyncio.Task(coroutine, loop=loop)
    task.add_done_callback(report_exception)
    return task    

