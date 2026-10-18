import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import conversion_status

class ConversionStatusTests(unittest.TestCase):
    def test_errors_without_warnings_are_partial(self):
        self.assertEqual(conversion_status(0,{'errors':['Missing model']}),'Partial conversion saved')
        self.assertEqual(conversion_status(0,{'status':'partial'}),'Partial conversion saved')
        self.assertEqual(conversion_status(0,{'unsupported':['Rope particle']}),'Partial conversion saved')
    def test_failure_takes_priority_and_warnings_remain_visible(self):
        self.assertEqual(conversion_status(1,{'status':'partial'}),'Failed')
        self.assertEqual(conversion_status(0,{'status':'failed'}),'Failed')
        self.assertEqual(conversion_status(0,{'warnings':['Approximate lighting']}),'Saved with warnings')
        self.assertEqual(conversion_status(0,{'status':'converted'}),'Saved')

if __name__=='__main__':unittest.main()
