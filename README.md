# nut_cloud

This package uses flask to create a simple website which uses sqlite3 as the backend database.

## Feature

1. Shop
2. Cloud drive

## Direction
The direction of usage:
1. Download the compressed package and enter the root directory (the following operations are all in the root directory)
2. exe `pip install -e`
3. Set up the environment
Linux: 
```
export FLASK_APP="nut_cloud"
export FLASK_ENV="development"
``` 
Powershell: 
```
$env:FLASK_APP="nut_cloud"
$env:FLASK_ENV="development"
```
4. `flask init-db`
5. `flask run`

## CAUTION

You need to configure the app_secret_key yourself!

## Language

English

## License

Copyright (c) 2018-2019 Chijun Sima

Licensed under the MIT License.
