"""One frozen interface for selected and ablation predictors."""
import json
from pathlib import Path
from .common import file_hash
from .round2_model import load_checkpoint
from .round3_experts import Experts
from .round3_predictor import RoutedPredictor
from .round3_segment_selector import SegmentPredictor


class Deployment:
    def __init__(self, path, expected_sha256, device='cpu', batch_size=32):
        if file_hash(path)!=expected_sha256:raise ValueError('deployment bundle drift')
        self.bundle=json.loads(Path(path).read_text())
        bundle=self.bundle
        if bundle['version']!='round3-deployment-v1':raise ValueError('unknown deployment version')
        if bundle['test_labels_accessed'] or bundle['confirmation_labels_accessed']:
            raise ValueError('evaluation-selected deployment')
        if bundle['selected_method'] not in ('fixed','risk','top2'):raise ValueError('unknown selected method')
        expert_bundle=bundle['expert_bundle']
        # Routing normalization must be the same original-DRO training scale used
        # when validation records were generated; each expert keeps its own scale.
        checkpoint=expert_bundle['methods']['original_dro']['checkpoints'][0]
        if file_hash(checkpoint)!=expert_bundle['checkpoint_hashes'][checkpoint]:
            raise ValueError('routing scale checkpoint drift')
        _,scales=load_checkpoint(checkpoint)
        self.experts=Experts(expert_bundle,scales,device=device,batch_size=batch_size)
        self.fixed=SegmentPredictor(self.experts,bundle['fixed_selection'])
        self.routers={}

    def predictor(self,method='selected',seed=None):
        if method=='selected':method=self.bundle['selected_method']
        if method=='fixed':
            if seed is not None:raise ValueError('fixed selector has no training seed')
            return self.fixed
        if method not in ('risk','top2'):raise ValueError('unknown routed method')
        if seed is not None and seed not in (0,1,2):raise ValueError('unknown router seed')
        key=(method,seed)
        if key not in self.routers:
            paths=self.bundle['router_checkpoints']
            if seed is not None:paths=[paths[seed]]
            self.routers[key]=RoutedPredictor(self.experts,paths,self.bundle['router_checkpoint_hashes'],mixture=method=='top2')
        return self.routers[key]

    def predict(self,table,observed,values,method='selected',seed=None,diagnostics=False):
        return self.predictor(method,seed).predict(table,observed,values,diagnostics=diagnostics)
