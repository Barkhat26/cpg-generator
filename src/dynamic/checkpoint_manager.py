from taint_flow.taintflow import TaintFlow
from config import Config


class CheckpointManager:
    def __init__(self, project_name: str, taint_flows: list[TaintFlow]):
        self.project_name = project_name
        self.taint_flows = taint_flows
        self.sink_to_checkpoint_id = dict()

    def prepare(self):
        sinks = [tf.sink for tf in self.taint_flows]

        unique_sinks = []

        for sink in sinks:
            if sink not in unique_sinks:
                unique_sinks.append(sink)

        for idx, us in enumerate(unique_sinks):
            self.sink_to_checkpoint_id[us.shared_id] = idx + 1
            checkpoint_file =  Config.CHECKPOINTS_DIR / self.project_name / f'ch_{idx + 1}.txt'

            with open(checkpoint_file, "w") as f:
                f.write("")

    def get_checkpoint_value(self, shared_id: str):
        checkpoint_id = self.sink_to_checkpoint_id[shared_id]
        checkpoint_file = Config.CHECKPOINTS_DIR / self.project_name / f'ch_{checkpoint_id}.txt'
        return open(checkpoint_file).read().strip()
