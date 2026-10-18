import math,random,unittest
from particle_plane_force_history import History
from particle_plane_force_motion import simulate
from particle_clock_prepared import PreparedInverse
from particle_clock_inverse import real_time
from particle_sim import Segment

class MotionHistoryTests(unittest.TestCase):
    def test_sparse_history_matches_reference_out_of_order(self):
        forces=[{'Max Distance from plane':200.,'Force at Max distance':(0,0,-75.)},
                {'Control point number':1,'Plane Normal':(2,0,0),'Force at Min distance':(1,0,0)}]
        target=lambda cp,t:(math.sin(t+cp),t*.2,0.)
        options={'gravity':(0,0,-9),'drag':.3,'birth_clock':2.}
        history=History((1,2,3),(4,-2,1),forces,target,**options)
        ages=[i/30 for i in range(61)]+[.003,.019]
        ages.extend(math.nextafter(i/120,d) for i in (1,29,30,31,239) for d in (0.,math.inf))
        random.Random(731).shuffle(ages)
        for age in ages:
            self.assertEqual(history.query(age),simulate((1,2,3),(4,-2,1),age,forces,target,**options))
        self.assertLessEqual(len(history.states),10)

    def test_invalid_history_inputs_and_ages_rejected(self):
        for options in ({'drag':-1},{'birth_clock':float('nan')},{'gravity':(0,0)}):
            with self.subTest(options=options),self.assertRaises(ValueError):
                History((0,0,0),(0,0,0),[],lambda cp,t:(0,0,0),**options)
        history=History((0,0,0),(0,0,0),[],lambda cp,t:(0,0,0))
        for age in (-1,float('nan'),1000):
            with self.assertRaises(ValueError):history.query(age)

    def test_prepared_inverse_matches_pauses_ramps_and_minimum_filters(self):
        segments=[Segment(0,1,True,True,1,2),Segment(1,2,True,False),Segment(2,3,True,True,2,1)]
        prepared=PreparedInverse(segments)
        for clock in (0.,.25,1.,1.5,1.5-1e-11,1.5+1e-11,2.,3.):
            for side in ('left','right'):
                for minimum in (None,0.,1.5,2.5):
                    try:expected=real_time(segments,clock,side,minimum)
                    except ValueError:
                        with self.assertRaises(ValueError):prepared.query(clock,side,minimum)
                    else:self.assertEqual(prepared.query(clock,side,minimum),expected)

    def test_prepared_inverse_invalid_queries_rejected(self):
        with self.assertRaises(ValueError):PreparedInverse([])
        prepared=PreparedInverse([Segment(0,1)])
        for clock,side,minimum in ((-1,'right',None),(2,'right',None),(0,'bad',None),(0,'right',2)):
            with self.assertRaises(ValueError):prepared.query(clock,side,minimum)
