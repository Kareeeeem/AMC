# API Docs

## TOC

* [What you need to know](#what-you-need-to-know)
* [Auth](#auth)
* [Endpoints](#endpoints)
    * `v1/users` methods: `GET`, `POST`
    * `v1/users/<user_id>` methods: `GET`, `PUT`, `DELETE`
    * `v1/users/<user_id>/favorites` methods: `GET`, `POST`
    * `v1/exercises` methods: `GET`, `POST`
    * `v1/exercises/<exercise_id>` methods: `GET`, `PUT`, `DELETE`
    * `v1/categories` methods: `GET`

## What you need to know

All endpoints receive and send json (`Content-Type: application/json`)
**EXCEPT** `/v1/login`. See [Auth](#endpoints) for details.

All `DELETE` requests return an empty body with 204 status code.

All Error messages have the following structure, where `message` could
be a string or an array of errors.
```
HTTP/1.0 400 BAD REQUEST
Content-Length: 141
Content-Type: application/json
Date: Sat, 21 May 2016 15:10:37 GMT
Server: Werkzeug/0.11.5 Python/2.7.11+

{
    "errors": {
        "message": {
            "password": [
                "Missing data for required field."
            ],
            "username": [
                "Missing data for required field."
            ]
        },
        "status_code": 400
    }
}
```

For `POST` and `PUT` only the fields contained in the `data` key of a
resource are valid. For the required fields check the example requests.

All `related` attributes are expandable by specifying them in the
`expand` query parameter (comma seperated). **EXCEPT** for `rating`

Collection resources return pagination objects containing URI's to
first, prev, next, current and last pages alongside information about
number of pages and items. Pagination is customized with the `per_page`
and `page` query parameters.

```
{
    "current": "/v1/exercises?per_page=10&page=1",
    "first": "/v1/exercises?per_page=10&page=1",
    "items": [
        ...
    ],
    "last": "/v1/exercises?per_page=10&page=51",
    "next": "/v1/exercises?per_page=10&page=2",
    "page": 1,
    "pages": 11,
    "per_page": 10,
    "prev": null,
    "total": 101
}
```

## Auth

The api follows this [guide] for handling auth. It's the OAuth2 password
grant flow. The steps are as follows.

1. Send a POST request to `/v1/login`.
    `Content-Type: application/www-x-form-urlencoded`
    The form has to contain the following fields. Where grant_type is
    always "password".

    * grant_type='password'
    * username=[USERNAMEOREMAIL]
    * password=[PASSWORD]

2. The server responds with a JSON Web Token.
    ```
    HTTP/1.0 200 OK
    Content-Length: 209
    Content-Type: application/json
    Date: Sat, 21 May 2016 15:00:21 GMT
    Location: http://localhost:5000/v1/users/8n5YvV
    Server: Werkzeug/0.11.5 Python/2.7.11+

    {
        "access_token": "eyJhbGciOiJIUzI1NiIsImV4cCI6MTQ2NjQzNDgyMSwiaWF0IjoxNDYzODQyODIxfQ.eyJpZCI6Nzk0MzQxMTd9.QUFhTX0-TV3PZmyzrn2JQyUpPGTdeiFLrSDOtnGe2fU",
        "expires_in": 2592000,
        "token_type": "Bearer"
    }
    ```
    `expires_in` tells us in how many seconds the token will expire.
    `token_type` tells us what kind of token it is. For now we only
    support the `Bearer` type.
    The location header tells us where the profile of the authenticated
    user is found.
    Requests are then made by adding the Authorization header.
    `Authorization: Bearer eyJhbGciOiJIUzI1NiIsImV4cCI6MTQ2NjQzNDgyMSwiaWF0IjoxNDYzODQyODIxfQ.eyJpZCI6Nzk0MzQxMTd9.QUFhTX0-TV3PZmyzrn2JQyUpPGTdeiFLrSDOtnGe2fU`


## Endpoints

### `/v1/users`
* methods: GET, POST
* example `GET` response
    ```
    HTTP/1.0 200 OK
    Content-Length: 3980
    Content-Type: application/json
    Date: Sat, 21 May 2016 19:02:25 GMT
    Server: Werkzeug/0.11.5 Python/2.7.11+

    {
        "current": "/v1/users?per_page=10&page=1",
        "first": "/v1/users?per_page=10&page=1",
        "items": [
            {
                "data": {
                    "username": "user0"
                },
                "meta": {
                    "href": "/v1/users/1K2AlRM",
                    "id": "1K2AlRM"
                },
                "related": {
                    "authored_exercises": "/v1/exercises?author=user0",
                    "favorite_exercises": "/v1/users/1K2AlRM/favorites"
                }
            },
            {
                "data": {
                    "username": "user1"
                },
                "meta": {
                    "href": "/v1/users/zPy9014",
                    "id": "zPy9014"
                },
                "related": {
                    "authored_exercises": "/v1/exercises?author=user1",
                    "favorite_exercises": "/v1/users/zPy9014/favorites"
                }
            },
            ...
            {
                "data": {
                    "username": "user9"
                },
                "meta": {
                    "href": "/v1/users/eqnP24",
                    "id": "eqnP24"
                },
                "related": {
                    "authored_exercises": "/v1/exercises?author=user9",
                    "favorite_exercises": "/v1/users/eqnP24/favorites"
                }
            }
        ],
        "last": "/v1/users?per_page=10&page=1",
        "next": null,
        "page": 1,
        "pages": 1,
        "per_page": 10,
        "prev": null,
        "total": 10
    }
    ```
* example `POST` request

    ```
    {
        "username": "kareem",
        "password": "1234hoedjevanpapier"
    }
    ```

* example `POST` response

    ```
    HTTP/1.0 201 CREATED
    Content-Length: 466
    Content-Type: application/json
    Date: Sat, 21 May 2016 15:12:35 GMT
    Location: /v1/users/OXy00BO
    Server: Werkzeug/0.11.5 Python/2.7.11+

    {
        "data": {
            "email": null,
            "username": "kareem"
        },
        "meta": {
            "created_at": "2016-05-21T15:12:35.256880+00:00",
            "href": "/v1/users/OXy00BO",
            "id": "OXy00BO",
            "last_login": null,
            "updated_at": "2016-05-21T15:12:35.256896+00:00"
        },
        "related": {
            "authored_exercises": "/v1/exercises?author=blah",
            "favorite_exercises": "/v1/users/OXy00BO/favorites"
        }
    }
    ```

### `/v1/users/<id>`
* methods: GET, PUT, DELETE
* example PUT request

    ```
        {
            "username": "lowercasekareem",
            "email": "kareem@blah.com"
        }
    ```
* example PUT response

    ```
    {
        "data": {
            "email": "kareem@blah.com",
            "username": "lowercasekareem"
        },
        "meta": {
            "created_at": "2016-05-21T15:12:35.256880+00:00",
            "href": "/v1/users/OXy00BO",
            "id": "OXy00BO",
            "last_login": "2016-05-23T16:30:35.25640+00:00",
            "updated_at": "2016-05-21T15:12:35.256896+00:00"
        },
        "related": {
            "authored_exercises": "/v1/exercises?author=blah",
            "favorite_exercises": "/v1/users/OXy00BO/favorites"
        }
    }
    ```
* example GET response (without token)

    ```
    {
        "data": {
            "username": "lowercasekareem"
        },
        "meta": {
            "href": "/v1/users/OXy00BO",
            "id": "OXy00BO",
        },
        "related": {
            "authored_exercises": "/v1/exercises?author=blah",
            "favorite_exercises": "/v1/users/OXy00BO/favorites"
        }
    },
    ```
* example GET response (with token)

    ```
    {
        "data": {
            "username": "lowercasekareem"
        },
        "meta": {
            "created_at": "2016-05-21T15:12:35.256880+00:00",
            "href": "/v1/users/OXy00BO",
            "id": "OXy00BO",
            "last_login": "2016-05-23T16:30:35.25640+00:00",
            "updated_at": "2016-05-21T15:12:35.256896+00:00"
        },
        "related": {
            "authored_exercises": "/v1/exercises?author=blah",
            "favorite_exercises": "/v1/users/OXy00BO/favorites"
        }
    },
    ```

## Exercise endpoints

### `v1/exercises`

* methods: POST, GET
* Token required (POST)
* Content-Type: application/json
* allowed query params (all optional):
    * search (string)
    * category (see category endpoint for available categories)
    * order_by (one of the following):
        * created_at
        * updated_at
        * average_rating
        * fun_rating
        * clear_rating
        * effective_rating
        * relevance (of search results)
        * popularity

* example POST data

    ```
    {
        "title": "new exercise",
        "description": "new description man",
        "category": "relaxatie",
        "duration": {"min": 0, "max": 5"}
    }
    ```

* example POST response
    ```
    HTTP/1.0 201 CREATED
    Content-Length: 806
    Content-Type: application/json
    Date: Sat, 21 May 2016 16:25:47 GMT
    Location: http://localhost:5000/v1/exercises/go5yOQz
    Server: Werkzeug/0.11.5 Python/2.7.11+

    {
	"data": {
	    "category": "relaxatie",
	    "description": "new description man",
	    "difficulty": 0,
	    "duration": {
		"max": 5,
		"min": 0
	    },
	    "group_exercise": false,
	    "json": {},
	    "private_exercise": false,
	    "title": "new exercise"
	},
	"meta": {
	    "average_rating": {
		"clear": null,
		"effective": null,
		"fun": null,
		"rating": null
	    },
	    "created_at": "2016-05-21T16:25:47.115088+00:00",
	    "edit_allowed": true,
	    "href": "http://localhost:5000/v1/exercises/go5yOQz",
	    "id": "go5yOQz",
	    "popularity": 2.8,
	    "updated_at": "2016-05-21T16:25:47.115103+00:00"
	},
	"related": {
	    "author": "http://localhost:5000/v1/users/zPy9014",
	    "rating": "http://localhost:5000/v1/exercises/go5yOQz/ratings"
	}
    }
    ```

* example GET response
```
    HTTP/1.0 200 OK
    Content-Length: 2305
    Content-Type: application/json
    Date: Sat, 21 May 2016 16:30:47 GMT
    Server: Werkzeug/0.11.5 Python/2.7.11+

    {
	"current": "http://localhost:5000/v1/exercises?per_page=2&order_by=average_rating&page=1",
	"first": "http://localhost:5000/v1/exercises?per_page=2&order_by=average_rating&page=1",
	"items": [
	    {
		"data": {
		    "category": "overig",
		    "description": "desc41",
		    "difficulty": 0,
		    "duration": {
			"max": 15,
			"min": 5
		    },
		    "group_exercise": false,
		    "json": null,
		    "private_exercise": false,
		    "title": "title41"
		},
		"meta": {
		    "average_rating": {
			"clear": 5,
			"effective": 4,
			"fun": 4,
			"rating": 4.33333333333333
		    },
		    "created_at": "2016-05-21T16:21:10.778219+00:00",
		    "edit_allowed": true,
		    "href": "http://localhost:5000/v1/exercises/O5W9wmK",
		    "id": "O5W9wmK",
		    "popularity": 3.0,
		    "updated_at": "2016-05-21T16:21:10.778240+00:00"
		},
		"related": {
		    "author": "http://localhost:5000/v1/users/kRr89bn",
		    "rating": "http://localhost:5000/v1/exercises/O5W9wmK/ratings"
		}
	    },
	    {
		"data": {
		    "category": "relaxatie",
		    "description": "desc26",
		    "difficulty": 0,
		    "duration": {
			"max": 5,
			"min": 0
		    },
		    "group_exercise": false,
		    "json": null,
		    "private_exercise": false,
		    "title": "title26"
		},
		"meta": {
		    "average_rating": {
			"clear": 2,
			"effective": 5,
			"fun": 5,
			"rating": 4.0
		    },
		    "created_at": "2016-05-21T16:21:10.733443+00:00",
		    "edit_allowed": true,
		    "href": "http://localhost:5000/v1/exercises/Pn9qMyL",
		    "id": "Pn9qMyL",
		    "popularity": 3.0,
		    "updated_at": "2016-05-21T16:21:10.733463+00:00"
		},
		"related": {
		    "author": "http://localhost:5000/v1/users/kR8WW2V",
		    "rating": "http://localhost:5000/v1/exercises/Pn9qMyL/ratings"
		}
	    }
	],
	"last": "http://localhost:5000/v1/exercises?per_page=2&order_by=average_rating&page=51",
	"next": "http://localhost:5000/v1/exercises?per_page=2&order_by=average_rating&page=2",
	"page": 1,
	"pages": 51,
	"per_page": 2,
	"prev": null,
	"total": 101
    }
```

### `v1/exercises/<id>`
* methods: GET, PUT, DELETE
* Token required
* Content-Type: application/json

### `v1/users/<id>/favorites`
* methods: GET, POST
* Token required
* Content-Type: application/json
* example GET response
Same as for `/v1/exercises` except that it only returns your favorites.
* example POST request
    ```
        {"id": "Pn9qMyL", "action": "favorite"}
    ```
* example response
    ```
    HTTP/1.0 204 NO CONTENT
    Content-Length: 0
    Content-Type: application/json
    Date: Sat, 21 May 2016 16:50:11 GMT
    Server: Werkzeug/0.11.5 Python/2.7.11+
    ```

[guide]: https://stormpath.com/blog/the-ultimate-guide-to-mobile-api-security
