"""Third-round six-method rules; reuse strict isolated fixed-layout audit machinery."""
import argparse
import json
import shutil
import time
from pathlib import Path
import numpy as np
import torch
from .common import ROOT, read_tables, write_json, file_hash
from .budget import allocation
from .sampling import mask
from .round3_deployment import Deployment
from .round2_downstream import UPSTREAM, SOURCES, external_imports, audit_case
from .round3_layout_contract import capture, verify_inputs, verify_state

METHODS=('linear','pchip','original_dro','hard_local','gated_none','round3_selected')
MASKS=(11,29,47,71,101)


def source_hashes():
    paths=[Path(__file__).resolve()]+[ROOT/'pdkcap'/name for name in
        ('round2_downstream.py','round3_layout_contract.py','round3_deployment.py','round3_experts.py','round3_predictor.py',
         'round3_segment_selector.py','round3_router.py','round3_support.py','round3_batch.py','round2_model.py','model.py','interpolation.py','sampling.py')]
    paths += [UPSTREAM/'openrcbench'/name for name in ('export.py','openrcx.py','spef.py')]
    return {str(p):file_hash(p) for p in paths}


class DownstreamPredictor:
    def __init__(self,deployment):self.deployment=deployment

    def all(self,table,observed,values,names=METHODS):
        if tuple(names)!=METHODS:raise ValueError('unexpected downstream method set')
        old=self.deployment.experts.all(table,observed,values,names=METHODS[:-1])
        if not old['valid'].all():raise ValueError('inapplicable downstream expert')
        output={name:dict(prediction=old['predictions'][i]) for i,name in enumerate(METHODS[:-1])}
        output['round3_selected']=dict(prediction=self.deployment.predict(table,observed,values))
        return output


def export_rules(bundle_path,expected_sha256,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    export_openrcx,_,parse_openrcx=external_imports()
    if file_hash(bundle_path)!=expected_sha256:raise ValueError('deployment bundle drift')
    if json.loads(Path(bundle_path).read_text())['domain']!='public':raise ValueError('downstream requires public-rule deployment')
    inputs=[UPSTREAM/'data/processed/dataset.jsonl',ROOT/'runs/public_inventory_v1/tables.jsonl']
    inputs += [UPSTREAM/'data/raw'/relative for _,_,relative in SOURCES]
    input_hashes={str(p):file_hash(p) for p in inputs}
    write_json(output/'FROZEN.json',dict(deployment_sha256=expected_sha256,source_hashes=source_hashes(),
        input_hashes=input_hashes,scope='six methods; five unique masks; 29 shared between historical and supplemental groups'))
    raw=UPSTREAM/'data/processed/dataset.jsonl';raw_tables={t['table_id']:t for t in read_tables(raw)}
    public_path=ROOT/'runs/public_inventory_v1/tables.jsonl';public=read_tables(public_path)
    predictor=DownstreamPredictor(Deployment(bundle_path,expected_sha256))
    methods=METHODS;exports=[];goldens=[]
    for platform,source_id,relative in SOURCES:
        original=UPSTREAM/'data/raw'/relative;folder=output/platform;folder.mkdir()
        golden=folder/'golden.rules';shutil.copy2(original,golden)
        source_tables=[t for t in raw_tables.values() if t['source_id']==source_id]
        source_rows=sum(len(t['rows']) for t in source_tables)
        if not source_tables:raise ValueError('missing exact source identity')
        goldens.append(dict(platform=platform,path=str(golden.resolve()),sha256=file_hash(golden),original=str(original.resolve()),source_id=source_id))
        selected=[t for t in public if t['partition']=='test' and t['source_id']==source_id]
        if not selected:raise ValueError('no PDKCap test tables for downstream source')
        for ratio in (.3,.5):
            for seed in MASKS:
                payloads={m:{'tables':{}} for m in methods};hidden_ids=[]
                for t in selected:
                    x=np.asarray(t['coordinates']);y=np.asarray(t['labels']);o,q=mask(x,'block',ratio,seed)
                    predictions=predictor.all(t,o,y[o],methods)
                    # PDKCap regrouping preserves source identity but changes table ids.
                    mapping={}
                    for sid in t['source_table_ids']:
                        source=raw_tables[sid]
                        if source['source_id']!=source_id:raise ValueError('cross-source identity merge')
                        for index,row in enumerate(source['rows']):
                            coord=(source['width'],row['spacing_left'],row['spacing_right'])
                            mapping.setdefault(coord,[]).append((sid,index,row))
                    for i in q:
                        key=tuple(x[i]);matches=mapping.get(key,[])
                        if not matches:raise ValueError('hidden coordinate has no original row')
                        for sid,index,row in matches:
                            np.testing.assert_array_equal(y[i],[row['coupling_cap'],row['ground_cap']])
                            hidden_ids.append((sid,index))
                            for method in methods:
                                value=predictions[method]['prediction'][i]
                                payloads[method]['tables'].setdefault(sid,{})[str(index)]={k:float(v) for k,v in zip(('coupling_cap','ground_cap'),value)}
                if len(hidden_ids)!=len(set(hidden_ids)):raise ValueError('duplicate export ownership')
                for method in methods:
                    name=f'{method}_block{int(ratio*100)}_mask{seed}';predfile=folder/f'{name}.json'
                    write_json(predfile,payloads[method]);out=folder/f'{name}.rules'
                    result=export_openrcx(original,raw,predfile,out,source_id=source_id)
                    exemplar=source_tables[0]
                    parsed={t.table_id:t for t in parse_openrcx(out,source_id=source_id,process_id=exemplar['process_id'],corner_id=exemplar['corner_id'])}
                    if set(parsed)!={t['table_id'] for t in source_tables}:raise ValueError('export table set changed')
                    actual=0
                    for source in source_tables:
                        if len(source['rows'])!=len(parsed[source['table_id']].rows):raise ValueError('export row count changed')
                        for i,(before,after) in enumerate(zip(source['rows'],parsed[source['table_id']].rows)):
                            changes=payloads[method]['tables'].get(source['table_id'],{}).get(str(i),{})
                            for field,value in before.items():
                                if field not in changes and after[field]!=value:raise ValueError('unmasked field or resistance changed')
                            for field,value in changes.items():
                                if not np.isclose(after[field],value,rtol=1e-8,atol=1e-12):raise ValueError('exported prediction differs from payload')
                            actual+=int(any(after[k]!=before[k] for k in ('coupling_cap','ground_cap')))
                    exports.append(dict(platform=platform,method=method,ratio=ratio,mask_seed=seed,path=str(out.resolve()),sha256=file_hash(out),
                        predictions_sha256=file_hash(predfile),source_id=source_id,source_rows=source_rows,test_tables=len(selected),
                        masked_rows=len(hidden_ids),changed_numeric_rows=actual,changed_numeric_row_fraction=actual/source_rows,**result))
    if any(file_hash(path)!=sha for path,sha in input_hashes.items()):raise ValueError('source inputs changed during export')
    write_json(output/'manifest.json',dict(bundle_sha256=file_hash(bundle_path),public_sha256=file_hash(public_path),raw_sha256=file_hash(raw),
        exporter_sha256=file_hash(__file__),upstream_exporter_sha256=file_hash(UPSTREAM/'openrcbench/export.py'),
        methods=list(methods),mask_groups={'historical':[11,29,47],'supplemental':[29,71,101]},unique_masks=list(MASKS),goldens=goldens,exports=exports,scope='PDKCap held-out capacitance fields only; exact original R preserved'))


def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    export=sub.add_parser('export');export.add_argument('--bundle',type=Path,required=True)
    export.add_argument('--sha256',required=True);export.add_argument('--output',type=Path,required=True)
    audit=sub.add_parser('audit');audit.add_argument('--manifest',type=Path,required=True)
    audit.add_argument('--platform',choices=[s[0] for s in SOURCES],required=True)
    audit.add_argument('--design',choices=['aes','ibex'],required=True);audit.add_argument('--output',type=Path,required=True)
    audit.add_argument('--deadline-unix',type=float)
    args=parser.parse_args()
    if args.command=='export':
        with allocation('training','round3 downstream export '+str(args.output),3600):
            export_rules(args.bundle,args.sha256,args.output)
    else:
        manifest=json.loads(args.manifest.read_text())
        frozen=json.loads((args.manifest.parent/'FROZEN.json').read_text())
        if source_hashes()!=frozen['source_hashes']:raise ValueError('downstream source drift')
        if tuple(manifest['methods'])!=METHODS or tuple(manifest['unique_masks'])!=MASKS:
            raise ValueError('wrong downstream method/mask protocol')
        golden=next(g for g in manifest['goldens'] if g['platform']==args.platform)
        selected=[v for v in manifest['exports'] if v['platform']==args.platform]
        expected={(method,ratio,seed) for method in METHODS for ratio in (.3,.5) for seed in MASKS}
        if len(selected)!=60 or {(v['method'],v['ratio'],v['mask_seed']) for v in selected}!=expected:
            raise ValueError('incomplete candidate rule population')
        contract=capture(args.platform,args.design)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        frozen_path=args.output.parent/(args.output.name+'.FROZEN.json')
        if frozen_path.exists():raise FileExistsError(frozen_path)
        write_json(frozen_path,dict(layout=contract,manifest_sha256=file_hash(args.manifest),source_hashes=source_hashes()))
        verify_inputs(contract)
        def bounded_variants():
            for variant in [dict(golden,method='golden'),*selected]:
                if args.deadline_unix is not None and time.time()+910>args.deadline_unix:
                    raise RuntimeError('downstream stage budget cannot cover another state; completed states retained')
                yield variant
        audit_case(args.platform,args.design,bounded_variants(),args.output)
        verify_inputs(contract)
        receipt=json.loads((args.output/'COMPLETED.json').read_text())
        for name,sha in receipt['state_hashes'].items():
            state_path=args.output/f'{name}.json'
            if file_hash(state_path)!=sha:raise ValueError('state drift after audit')
            verify_state(contract,json.loads(state_path.read_text()))
        write_json(args.output/'ROUND3_VERIFIED.json',dict(passed=True,layout_freeze_sha256=file_hash(frozen_path),
            completed_sha256=file_hash(args.output/'COMPLETED.json'),states=receipt['states']))


if __name__=='__main__':main()
