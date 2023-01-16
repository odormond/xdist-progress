import pytest
from _pytest.terminal import TerminalReporter
from rich.console import Group
from rich.live import Live
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Column
from xdist.dsession import DSession


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    if config.getoption("dist") == "no" or not config.getoption("tx"):
        return
    manager = config.pluginmanager
    manager.unregister(manager.getplugin('terminalreporter'))
    manager.unregister(manager.getplugin('dsession'))
    manager.unregister(manager.getplugin('terminaldistreporter'))
    manager.register(MyTerminalReporter(config), 'terminalreporter')
    manager.register(MyDSession(config), 'dsession')


class MyTerminalReporter(TerminalReporter):
    def setup_progress(self, total):
        label_column = Column(width=7)  # length of "[total]"
        cnt_column = Column(width=len(str(total)))

        self.gateway_progress = Progress(
            TextColumn(r'[bold]\[{task.description}]', table_column=label_column),
            TextColumn('[bold green]{task.fields[passed]}', table_column=cnt_column),
            TextColumn('[green]{task.fields[xfailed]}', table_column=cnt_column),
            TextColumn('[bold yellow]{task.fields[skipped]}', table_column=cnt_column),
            TextColumn('[red]{task.fields[xpassed]}', table_column=cnt_column),
            TextColumn('[bold red]{task.fields[failed]}', table_column=cnt_column),
            TextColumn('[magenta]{task.fields[error]}', table_column=cnt_column),
            TimeElapsedColumn(),
            TextColumn('{task.fields[nodeid]}'),
            expand=False,
            refresh_per_second=4,
        )
        self.total_progress = Progress(
            TextColumn(r'[bold]\[total]', table_column=label_column),
            TextColumn('[bold green]{task.fields[passed]}', table_column=cnt_column),
            TextColumn('[green]{task.fields[xfailed]}', table_column=cnt_column),
            TextColumn('[bold yellow]{task.fields[skipped]}', table_column=cnt_column),
            TextColumn('[red]{task.fields[xpassed]}', table_column=cnt_column),
            TextColumn('[bold red]{task.fields[failed]}', table_column=cnt_column),
            TextColumn('[magenta]{task.fields[error]}', table_column=cnt_column),
            TimeElapsedColumn(),
            BarColumn(),
            MofNCompleteColumn(),
            expand=False,
            refresh_per_second=4,
        )
        self.rich_live = Live(
            Group(self.gateway_progress, self.total_progress),
            refresh_per_second=4,
            transient=True,
        )
        self.gateways = {}
        self.totals = dict(passed=0, xfailed=0, skipped=0, xpassed=0, failed=0, error=0, warning=0)
        self.total_task_id = self.total_progress.add_task('total', total=total, **self.totals)

    def logstart(self, node, nodeid):
        gateway = node.gateway.id
        nodeid = nodeid.replace('[', r'\[')  # Prevent rich from interpreting the test parameters
        if not self.gateways:
            self.rich_live.start()
        if gateway not in self.gateways:
            counts = {k: 0 for k in self.totals}
            task_id = self.gateway_progress.add_task(gateway, total=None, nodeid=nodeid, **counts)
            self.gateways[gateway] = task_id, counts
        else:
            task_id, counts = self.gateways[gateway]
            self.gateway_progress.update(task_id, nodeid=nodeid, **counts)

    def pytest_runtest_logstart(self, nodeid, location):
        pass

    def pytest_runtest_logfinish(self, nodeid, location):
        pass

    def pytest_runtest_logreport(self, report):
        self._tests_ran = True
        category, letter, word = self.config.hook.pytest_report_teststatus(
            report=report, config=self.config
        )
        self._add_stats(category, [report])

        if category not in self.totals or category == 'error' and report.when == 'teardown':
            return

        gateway = report.node.gateway.id
        task_id, counts = self.gateways[gateway]
        counts[category] += 1
        self.totals[category] += 1
        self.gateways[gateway] = task_id, counts
        self.gateway_progress.update(task_id, nodeid='', **counts)
        self.total_progress.update(self.total_task_id, advance=1, **self.totals)

    def pytest_testnodedown(self, node, error):
        gateway = node.gateway.id
        if gateway in self.gateways:
            self.gateway_progress.stop_task(self.gateways.pop(gateway)[0])
        if not self.gateways:
            self.gateway_progress.stop()
            self.total_progress.stop()
            self.rich_live.stop()


class MyDSession(DSession):
    def worker_logstart(self, node, nodeid, location):
        super().worker_logstart(node, nodeid, location)
        self.terminal.logstart(node, nodeid)

    def worker_collectionfinish(self, node, ids):
        super().worker_collectionfinish(node, ids)
        if self.sched.collection_is_completed:
            self.terminal.setup_progress(len(self.sched.collection))
