from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IntegrationAssetTests(unittest.TestCase):
    def test_native_layout_preserves_widgets_launchers_and_is_idempotent(self):
        harness = r'''
const fs = require('fs');
let next=1; const ps=[];
function widget(type) {return {type,configGroup:[],writeConfig(k,v){this[k]=v;},reloadConfig(){},readConfig(k,d){return this[k] ?? d;}};}
global.Panel=function(){this.id=next++;this.screen=0;this.ws=[];this.widgets=()=>this.ws;this.addWidget=(t)=>{let w=widget(t);this.ws.push(w);return w;};this.configGroup=[];this.writeConfig=(k,v)=>this[k]=v;ps.push(this);};
global.panels=()=>ps;global.print=()=>{};
let p=new Panel();p.location='top';p.addWidget('org.kde.plasma.appmenu');p.addWidget('my.custom.widget');
let d=new Panel();d.location='bottom';let task=d.addWidget('org.kde.plasma.icontasks');task.launchers='my-pinned-app';
const code=fs.readFileSync(process.argv[1],'utf8');eval(code);eval(code);
if(ps.length!==2)throw Error('duplicate panels');
if(p.height!==34 || p.floating!==true)throw Error('top geometry');   // full-width floating bar: the theme removes the gap so the bottom corners can be round
if(d.height!==64 || d.lengthMode!=='fit' || d.floating!==true)throw Error('dock geometry');
if(!p.ws.some(w=>w.type==='my.custom.widget'))throw Error('lost custom widget');
if(task.launchers!=='my-pinned-app')throw Error('lost launchers');
if(p.ws.filter(w=>w.type==='org.kde.plasma.appmenu').length!==1)throw Error('duplicated global menu');
console.log('PASS: native panel semantics and idempotence');
'''
        result = subprocess.run(['node', '-e', harness, str(ROOT / 'assets/layout.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_clock_shows_time_only_unless_the_date_is_requested(self):
        harness = r'''
const fs = require('fs');
function widget(type) {return {type,writeConfig(k,v){this[k]=v;},reloadConfig(){},readConfig(k,d){return this[k] ?? d;},widgets(){return [];}};}
function run(options) {
  const ps=[]; let next=1;
  global.Panel=function(){this.id=next++;this.screen=0;this.ws=[];this.widgets=()=>this.ws;this.addWidget=(t)=>{let w=widget(t);this.ws.push(w);return w;};ps.push(this);};
  global.panels=()=>ps;global.print=()=>{};
  global.DARWIN_OPTIONS=Object.assign({dock:false},options);
  eval(fs.readFileSync(process.argv[1],'utf8'));
  return ps[0].ws.find(w=>w.type==='org.kde.plasma.digitalclock');
}
const plain=run({}), dated=run({clockDate:true});
if(plain.showDate!==false||plain.fontSize!==7)throw Error('time-only clock: '+plain.showDate+' '+plain.fontSize);
if(plain.fontWeight!==400||plain.fontStyleName!=='Regular')throw Error('clock must use the regular interface weight');
const big=run({fontSize:12}); if(big.fontSize!==8)throw Error('clock must follow the interface font size (x0.7)');
if(dated.showDate!==true||dated.fontSize!==7)throw Error('dated clock: '+dated.showDate+' '+dated.fontSize);
console.log('PASS');
'''
        result = subprocess.run(['node', '-e', harness, str(ROOT / 'assets/layout.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_gtk_overrides_have_toolkit_specific_controls(self):
        for version, selector in [('3', 'button.titlebutton'), ('4', 'windowcontrols button')]:
            css = (ROOT / f'assets/gtk/gtk{version}.css')
            self.assertTrue(css.is_file(), str(css))
            self.assertIn(selector, css.read_text())
            self.assertIn('#ff736a', css.read_text())


if __name__ == '__main__':
    unittest.main()
