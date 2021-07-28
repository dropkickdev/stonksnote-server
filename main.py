from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.starlette import register_tortoise

from app.settings.db import DATABASE
from app.routes import authrouter, demorouter, grouprouter, permrouter, accountrouter
from app.fixtures.routes import fixturerouter
from tests.app.routes import testrouter

from trades.routes import traderoutes
from trades.fixtures.routes import tradesdevrouter


def get_app() -> FastAPI:
    app = FastAPI()     # noqa
    
    # Routes
    app.include_router(authrouter, prefix='/app', tags=['Auth'])
    app.include_router(accountrouter, prefix='/account', tags=['Account'])
    app.include_router(grouprouter, prefix='/group', tags=['Group'])
    app.include_router(permrouter, prefix='/permission', tags=['Permission'])
    app.include_router(traderoutes, prefix='/trades', tags=['Trades'])
    
    # Project fixtures
    app.include_router(fixturerouter, prefix='/fixtures', tags=['Fixtures'])
    
    # For local use only
    app.include_router(tradesdevrouter, prefix='/trades/dev', tags=['Local development only'])
    app.include_router(testrouter, prefix='/test', tags=['Development'])
    app.include_router(demorouter, prefix='/demo', tags=['Development'])
    
    
    # Tortoise
    register_tortoise(app, config=DATABASE, generate_schemas=True)

    # CORS
    origins = ['http://localhost:3000', 'https://localhost:3000']
    app.add_middleware(
        CORSMiddleware, allow_origins=origins, allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )
    
    return app

app = get_app()
