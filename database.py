import models

# This will create all the tables defined in the models
models.Base.metadata.create_all(bind=models.engine)
