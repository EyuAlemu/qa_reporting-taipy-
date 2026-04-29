import marshmallow
import marshmallow.fields as f
print('marshmallow module:', marshmallow)
print('fields.Inferred exists:', hasattr(f, 'Inferred'))
print('fields dir includes Inferred:', [name for name in dir(f) if 'Inferred' in name])
