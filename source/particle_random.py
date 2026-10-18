"""Stable approximate random streams for each particle effect instance."""
def seed(descriptor,definition):
    original=str(descriptor.get('random_seed'))+definition['name']
    occurrence=int(definition.get('random_instance_index',0))
    return original if occurrence==0 else original+':instance:'+str(occurrence)
