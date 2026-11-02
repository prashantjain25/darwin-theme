from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SpotlightPlacementTests(unittest.TestCase):
    def test_native_rule_positions_only_spotlight_on_its_output(self):
        path = ROOT / 'assets/kwin-scripts/darwin-spotlight-position/contents/code/main.js'
        program = r'''
const fs=require('fs');
let callback;
global.workspace={windowAdded:{connect(fn){callback=fn;}},windowList(){return [];},activeWindow:null};
eval(fs.readFileSync(process.argv[1],'utf8'));
let normal={resourceClass:'konsole',frameGeometry:{x:5,y:6,width:900,height:700}};
callback(normal); if(normal.frameGeometry.x!==5)throw Error('moved unrelated window');
let spotlight={resourceClass:'darwin-spotlight',desktopFileName:'darwin-spotlight',
frameGeometry:{x:0,y:0,width:640,height:100},output:{geometry:{x:2560,y:0,width:2560,height:1440}}};
callback(spotlight);
if(spotlight.frameGeometry.x!==2560+Math.round((2560-640)/2))throw Error('not centered on correct output');
if(spotlight.frameGeometry.y!==Math.round(1440*.22))throw Error('wrong vertical offset');
if(spotlight.keepAbove!==true)throw Error('not an overlay');
console.log('PASS: scoped Wayland compositor placement');
'''
        result = subprocess.run(['node', '-e', program, str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
