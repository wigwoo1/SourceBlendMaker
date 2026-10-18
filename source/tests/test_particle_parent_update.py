import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_parent_update import History,prepare,NAME
from particle_parent_buffer import Snapshot

def op(name,**p):return {'function':name,'parameters':p}
def snapshot(values,time=0):return Snapshot.capture(0,time,range(len(values)),values,[(x-1,y,z) for x,y,z in values])

class ParentUpdateTests(unittest.TestCase):
    def history(self,operators=None,query=None,births=None,lives=None):
        births=births or [SimpleNamespace(index=0,simulation_time=0.)]
        return History(operators or [op(NAME,**{'Inherited Field':0})],births,
                       lives or {b.index:10. for b in births},
                       {b.index:(0,0,0) for b in births},{b.index:(0,0,0) for b in births},
                       query or (lambda t,dt:snapshot([(10,0,0),(20,0,0),(30,0,0)],t)),step=.1)
    def test_cursor_persists_across_full_ticks(self):
        h=self.history()
        self.assertEqual([h.query(t)[0][0][0] for t in (.1,.2,.3,.4)],[10,20,30,10])
    def test_fractional_query_does_not_advance_stored_cursor(self):
        h=self.history();h.query(.15);h.query(.17)
        self.assertEqual(h.query(.2)[0][0][0],20)
    def test_out_of_order_queries_keep_identical_results(self):
        h=self.history();expected=h.query(.5)
        h.query(.1);h.query(.35)
        self.assertEqual(h.query(.5),expected)
        self.assertEqual(h.query(.3)[0][0][0],30)
    def test_each_module_has_independent_cursor(self):
        h=self.history([op(NAME,**{'Inherited Field':0,'Particle Increment Amount':2}),op(NAME,**{'Inherited Field':2})])
        h.query(.1)
        now,previous,_=h.query(.2)[0]
        self.assertEqual(now,(30,0,0));self.assertEqual(previous,(19,0,0))
    def test_disabled_modules_do_not_enter_prepared_pipeline(self):
        d={'modules':{'operators':[op(NAME,**{'Inherited Field':0,'operator enabled':False})]}}
        self.assertEqual(prepare(d),[])
    def test_birth_order_and_death_filter(self):
        births=[SimpleNamespace(index=i,simulation_time=t) for i,t in ((0,0),(1,.15))]
        h=self.history(births=births,lives={0:.25,1:1})
        self.assertEqual(set(h.query(.1)),{0})
        self.assertEqual(set(h.query(.2)),{0,1})
        self.assertEqual(set(h.query(.3)),{1})
    def test_parent_empty_preserves_movement(self):
        h=self.history([op('Movement Basic',gravity=(2,0,0)),op(NAME,**{'Inherited Field':0})],lambda t,dt:snapshot([],t))
        self.assertAlmostEqual(h.query(.2)[0][0][0],.06,places=5)
    def test_authored_movement_after_copy_changes_result(self):
        a=self.history([op(NAME,**{'Inherited Field':0}),op('Movement Basic')])
        b=self.history([op('Movement Basic'),op(NAME,**{'Inherited Field':0})])
        self.assertEqual(a.query(.1)[0][0][0],20)
        self.assertEqual(b.query(.1)[0][0][0],10)
    def test_random_queries_are_order_independent(self):
        ops=[op(NAME,**{'Inherited Field':0,'Random Parent Particle Distribution':True})]
        a=self.history(ops);b=self.history(ops)
        a.query(.15);a.query(.01)
        self.assertEqual(a.query(.5),b.query(.5))
    def test_prepare_rejects_unimplemented_scalar_field(self):
        with self.assertRaisesRegex(ValueError,'position'):
            prepare({'modules':{'operators':[op(NAME,**{'Inherited Field':16})]}})
    def test_prepare_rejects_nondefault_strength(self):
        with self.assertRaisesRegex(ValueError,'gates'):
            prepare({'modules':{'operators':[op(NAME,**{'Inherited Field':0,'operator time scale min':2})]}})
    def test_prepare_rejects_other_motion(self):
        with self.assertRaisesRegex(ValueError,'integration'):
            prepare({'modules':{'operators':[op(NAME,**{'Inherited Field':0}),op('Movement Lock to Control Point')]}})

if __name__=='__main__':unittest.main()
