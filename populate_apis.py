"""
Script to populate the database with initial API configurations
"""

import json
import os
from app import app, db
from models import APIConfiguration

# Define the APIs to add
APIS = [
    {
        "api_name": "Shodan",
        "api_url": "https://api.shodan.io",
        "api_key_env": "SHODAN_API_KEY",
        "description": "Shodan is a search engine for Internet-connected devices. It can be used to find specific types of devices, identify vulnerabilities, and gather intelligence on network infrastructure.",
        "endpoints": json.dumps({
            "host": {
                "path": "/shodan/host/{ip}",
                "method": "GET",
                "params": {
                    "key": "{api_key}",
                    "minify": "false"
                },
                "description": "Returns all available information for an IP address."
            },
            "search": {
                "path": "/shodan/host/search",
                "method": "GET",
                "params": {
                    "key": "{api_key}",
                    "query": "{query}",
                    "page": "1",
                    "minify": "false"
                },
                "description": "Search Shodan using the same query syntax as the website."
            }
        }),
        "format": json.dumps({
            "example": {
                "ip_str": "8.8.8.8",
                "ports": [53, 443],
                "hostnames": ["dns.google"]
            },
            "fields": {
                "ip_str": "IP address as a string",
                "ports": "List of open ports",
                "hostnames": "List of hostnames",
                "country_code": "2-letter country code",
                "org": "Organization",
                "data": "Array of banners"
            }
        })
    },
    {
        "api_name": "ZoomEye",
        "api_url": "https://api.zoomeye.org",
        "api_key_env": "ZOOMEYE_API_KEY",
        "description": "ZoomEye is a search engine for cyberspace that lets the user find specific network components (IP address, services, etc.).",
        "endpoints": json.dumps({
            "host_search": {
                "path": "/host/search",
                "method": "GET",
                "headers": {
                    "API-KEY": "{api_key}"
                },
                "params": {
                    "query": "{query}",
                    "page": "1",
                    "size": "20"
                },
                "description": "Search for host information."
            },
            "web_search": {
                "path": "/web/search",
                "method": "GET",
                "headers": {
                    "API-KEY": "{api_key}"
                },
                "params": {
                    "query": "{query}",
                    "page": "1",
                    "size": "20"
                },
                "description": "Search for web application information."
            }
        }),
        "format": json.dumps({
            "example": {
                "total": 123,
                "matches": [
                    {
                        "ip": "203.0.113.1",
                        "portinfo": {
                            "port": 80,
                            "service": "http"
                        },
                        "geoinfo": {
                            "country": {
                                "code": "US",
                                "name": "United States"
                            },
                            "city": {
                                "name": "San Francisco"
                            }
                        }
                    }
                ]
            }
        })
    },
    {
        "api_name": "Hunter",
        "api_url": "https://api.hunter.io/v2",
        "api_key_env": "HUNTER_API_KEY",
        "description": "Hunter lets you find email addresses in seconds and connect with the people that matter for your business.",
        "endpoints": json.dumps({
            "domain_search": {
                "path": "/domain-search",
                "method": "GET",
                "params": {
                    "domain": "{domain}",
                    "api_key": "{api_key}",
                    "limit": "10"
                },
                "description": "Search all email addresses found on the internet for a given domain."
            },
            "email_finder": {
                "path": "/email-finder",
                "method": "GET",
                "params": {
                    "domain": "{domain}",
                    "first_name": "{first_name}",
                    "last_name": "{last_name}",
                    "api_key": "{api_key}"
                },
                "description": "Generate or retrieve the most likely email address for a professional."
            },
            "email_verifier": {
                "path": "/email-verifier",
                "method": "GET",
                "params": {
                    "email": "{email}",
                    "api_key": "{api_key}"
                },
                "description": "Verify the deliverability of an email address."
            }
        }),
        "format": json.dumps({
            "example": {
                "data": {
                    "domain": "example.com",
                    "disposable": False,
                    "webmail": False,
                    "emails": [
                        {
                            "value": "john.doe@example.com",
                            "type": "personal",
                            "confidence": 90,
                            "first_name": "John",
                            "last_name": "Doe",
                            "position": "CTO",
                            "linkedin": "https://www.linkedin.com/in/johndoe",
                            "twitter": "johndoe",
                            "phone_number": None
                        }
                    ],
                    "pattern": "{first}@{domain}"
                }
            }
        })
    },
    {
        "api_name": "Numverify",
        "api_url": "http://apilayer.net/api",
        "api_key_env": "NUMVERIFY_API_KEY",
        "description": "Numverify offers a full-featured yet simple RESTful JSON API for national and international phone number validation and information lookup.",
        "endpoints": json.dumps({
            "validate": {
                "path": "/validate",
                "method": "GET",
                "params": {
                    "access_key": "{api_key}",
                    "number": "{phone_number}",
                    "country_code": "",
                    "format": "1"
                },
                "description": "Validate and get information about a phone number."
            }
        }),
        "format": json.dumps({
            "example": {
                "valid": True,
                "number": "14158586273",
                "local_format": "4158586273",
                "international_format": "+14158586273",
                "country_prefix": "+1",
                "country_code": "US",
                "country_name": "United States of America",
                "location": "Novato",
                "carrier": "AT&T Mobility LLC",
                "line_type": "mobile"
            }
        })
    },
    {
        "api_name": "WiGLE",
        "api_url": "https://api.wigle.net/api/v2",
        "api_key_env": "WIGLE_API_KEY",
        "description": "WiGLE (Wireless Geographic Logging Engine) is a platform for collecting information about wireless networks, including WiFi networks, Bluetooth devices, and cellular networks.",
        "endpoints": json.dumps({
            "search": {
                "path": "/network/search",
                "method": "GET",
                "params": {
                    "onlymine": "false",
                    "latrange1": "{lat_min}",
                    "latrange2": "{lat_max}",
                    "longrange1": "{long_min}",
                    "longrange2": "{long_max}",
                    "lastupdt": "",
                    "freenet": "false",
                    "paynet": "false",
                    "ssid": "{ssid}"
                },
                "headers": {
                    "Authorization": "Basic {encoded_auth}"
                },
                "description": "Search for wireless networks."
            },
            "detail": {
                "path": "/network/detail",
                "method": "GET",
                "params": {
                    "netid": "{netid}",
                    "ssid": "{ssid}"
                },
                "headers": {
                    "Authorization": "Basic {encoded_auth}"
                },
                "description": "Get detailed information about a specific network."
            }
        }),
        "format": json.dumps({
            "example": {
                "success": True,
                "totalResults": 1,
                "search_after": 0,
                "results": [
                    {
                        "trilat": 37.7798,
                        "trilong": -122.4221,
                        "ssid": "FreeWiFi",
                        "qos": 2,
                        "transid": "202012010000",
                        "firsttime": "2020-12-01T00:00:00.000Z",
                        "lasttime": "2021-01-01T00:00:00.000Z",
                        "lastupdt": "2021-01-01T00:00:00.000Z",
                        "encryption": "wpa2",
                        "country": "US",
                        "region": "CA",
                        "city": "San Francisco",
                        "road": "Market St",
                        "type": "infrastructure"
                    }
                ]
            }
        })
    },
    {
        "api_name": "Google Custom Search",
        "api_url": "https://www.googleapis.com/customsearch/v1",
        "api_key_env": "GOOGLE_API_KEY",
        "description": "Google Custom Search API allows you to create a custom search engine and programmatically retrieve results from it. It provides the capability to search for text, images, and more across a specific set of websites or the entire web.",
        "endpoints": json.dumps({
            "search": {
                "path": "",
                "method": "GET",
                "params": {
                    "key": "{api_key}",
                    "cx": "{search_engine_id}",
                    "q": "{query}",
                    "num": "10",
                    "start": "1",
                    "imgSize": "",
                    "imgType": "",
                    "searchType": ""
                },
                "description": "Search for web pages, images, and more."
            }
        }),
        "format": json.dumps({
            "example": {
                "kind": "customsearch#search",
                "items": [
                    {
                        "kind": "customsearch#result",
                        "title": "Example title",
                        "htmlTitle": "Example <b>title</b>",
                        "link": "https://example.com",
                        "displayLink": "example.com",
                        "snippet": "This is an example search result snippet that Google Custom Search might return.",
                        "htmlSnippet": "This is an example search result snippet that Google Custom Search might return.",
                        "formattedUrl": "https://example.com",
                        "pagemap": {
                            "metatags": [
                                {
                                    "viewport": "width=device-width, initial-scale=1",
                                    "og:title": "Example title",
                                    "og:description": "Example description"
                                }
                            ],
                            "cse_image": [
                                {
                                    "src": "https://example.com/image.jpg"
                                }
                            ]
                        }
                    }
                ]
            }
        })
    },
    {
        "api_name": "IPStack",
        "api_url": "http://api.ipstack.com",
        "api_key_env": "IPSTACK_API_KEY",
        "description": "ipstack offers one of the leading IP to geolocation APIs and global IP database services worldwide.",
        "endpoints": json.dumps({
            "lookup": {
                "path": "/{ip}",
                "method": "GET",
                "params": {
                    "access_key": "{api_key}"
                },
                "description": "Get geolocation information for an IP address."
            },
            "bulk": {
                "path": "/{ip_list}",
                "method": "GET",
                "params": {
                    "access_key": "{api_key}"
                },
                "description": "Get geolocation information for multiple IP addresses (comma-separated)."
            }
        }),
        "format": json.dumps({
            "example": {
                "ip": "134.201.250.155",
                "type": "ipv4",
                "continent_code": "NA",
                "continent_name": "North America",
                "country_code": "US",
                "country_name": "United States",
                "region_code": "CA",
                "region_name": "California",
                "city": "Los Angeles",
                "zip": "90013",
                "latitude": 34.0453,
                "longitude": -118.2413,
                "location": {
                    "geoname_id": 5368361,
                    "capital": "Washington D.C.",
                    "languages": [
                        {
                            "code": "en",
                            "name": "English",
                            "native": "English"
                        }
                    ],
                    "country_flag": "https://assets.ipstack.com/flags/us.svg",
                    "country_flag_emoji": "🇺🇸",
                    "country_flag_emoji_unicode": "U+1F1FA U+1F1F8",
                    "calling_code": "1",
                    "is_eu": False
                }
            }
        })
    },
    {
        "api_name": "GitHub",
        "api_url": "https://api.github.com",
        "api_key_env": "GITHUB_API_KEY",
        "description": "GitHub API provides programmatic access to GitHub's data and functionality, allowing you to search for users, repositories, and more.",
        "endpoints": json.dumps({
            "user": {
                "path": "/users/{username}",
                "method": "GET",
                "headers": {
                    "Authorization": "token {api_key}"
                },
                "description": "Get information about a GitHub user."
            },
            "user_repos": {
                "path": "/users/{username}/repos",
                "method": "GET",
                "headers": {
                    "Authorization": "token {api_key}"
                },
                "params": {
                    "sort": "updated",
                    "per_page": "10",
                    "page": "1"
                },
                "description": "Get a user's repositories."
            },
            "search_users": {
                "path": "/search/users",
                "method": "GET",
                "headers": {
                    "Authorization": "token {api_key}"
                },
                "params": {
                    "q": "{query}"
                },
                "description": "Search for GitHub users."
            }
        }),
        "format": json.dumps({
            "example": {
                "login": "octocat",
                "id": 583231,
                "avatar_url": "https://avatars.githubusercontent.com/u/583231?v=4",
                "html_url": "https://github.com/octocat",
                "type": "User",
                "name": "The Octocat",
                "company": "@github",
                "blog": "https://github.blog",
                "location": "San Francisco",
                "email": None,
                "bio": None,
                "twitter_username": None,
                "public_repos": 8,
                "public_gists": 8,
                "followers": 3938,
                "following": 9,
                "created_at": "2011-01-25T18:44:36Z",
                "updated_at": "2021-04-26T19:35:47Z"
            }
        })
    },
    {
        "api_name": "VirusTotal",
        "api_url": "https://www.virustotal.com/api/v3",
        "api_key_env": "VIRUSTOTAL_API_KEY",
        "description": "VirusTotal API allows you to scan and get reports about URLs, IP addresses, domains, and files.",
        "endpoints": json.dumps({
            "url_scan": {
                "path": "/urls",
                "method": "POST",
                "headers": {
                    "x-apikey": "{api_key}"
                },
                "data": {
                    "url": "{url}"
                },
                "description": "Submit a URL for scanning."
            },
            "url_report": {
                "path": "/urls/{id}",
                "method": "GET",
                "headers": {
                    "x-apikey": "{api_key}"
                },
                "description": "Get a URL scan report."
            },
            "ip_report": {
                "path": "/ip_addresses/{ip}",
                "method": "GET",
                "headers": {
                    "x-apikey": "{api_key}"
                },
                "description": "Get information about an IP address."
            },
            "domain_report": {
                "path": "/domains/{domain}",
                "method": "GET",
                "headers": {
                    "x-apikey": "{api_key}"
                },
                "description": "Get information about a domain."
            }
        }),
        "format": json.dumps({
            "example": {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "harmless": 75,
                            "malicious": 0,
                            "suspicious": 0,
                            "undetected": 8,
                            "timeout": 0
                        },
                        "reputation": 0,
                        "last_analysis_results": {
                            "CLEAN MX": {
                                "category": "harmless",
                                "result": "clean",
                                "method": "blacklist",
                                "engine_name": "CLEAN MX"
                            }
                        }
                    },
                    "type": "url",
                    "id": "cf4b367e49bf0b22041c6f065f4aa19f3cfe39c8d5abc0617343d1a66c6a26f5"
                }
            }
        })
    },
    {
        "api_name": "Clearbit",
        "api_url": "https://person.clearbit.com/v2",
        "api_key_env": "CLEARBIT_API_KEY",
        "description": "Clearbit's Person API lets you look up a person by their email address and returns rich data about them.",
        "endpoints": json.dumps({
            "person": {
                "path": "/people/find",
                "method": "GET",
                "headers": {
                    "Authorization": "Bearer {api_key}"
                },
                "params": {
                    "email": "{email}"
                },
                "description": "Find information about a person by their email address."
            }
        }),
        "format": json.dumps({
            "example": {
                "id": "d54c54ad-40be-4305-8a34-0ab44710b90d",
                "name": {
                    "givenName": "Alex",
                    "familyName": "MacCaw",
                    "fullName": "Alex MacCaw"
                },
                "email": "alex@example.com",
                "gender": "male",
                "location": "San Francisco, CA, US",
                "geo": {
                    "city": "San Francisco",
                    "state": "California",
                    "stateCode": "CA",
                    "country": "United States",
                    "countryCode": "US"
                },
                "bio": "Co-founder and CEO of Clearbit",
                "site": "http://alexmaccaw.com",
                "avatar": "https://d1ts43dypk8bqh.cloudfront.net/v1/avatars/d54c54ad-40be-4305-8a34-0ab44710b90d",
                "employment": {
                    "domain": "clearbit.com",
                    "name": "Clearbit",
                    "title": "CEO",
                    "role": "leadership",
                    "seniority": "executive"
                },
                "facebook": {
                    "handle": "amaccaw"
                },
                "github": {
                    "handle": "maccman",
                    "avatar": "https://avatars.githubusercontent.com/u/2142?v=2",
                    "company": "Clearbit",
                    "blog": "http://alexmaccaw.com",
                    "followers": 2932,
                    "following": 94
                },
                "twitter": {
                    "handle": "maccaw",
                    "id": "2006261",
                    "bio": "something",
                    "followers": 15249,
                    "following": 1068,
                    "location": "San Francisco",
                    "site": "http://alexmaccaw.com",
                    "avatar": "https://pbs.twimg.com/profile_images/378800000078594392/cf160c1c86bf39da40aecb2742856b49_normal.jpeg"
                },
                "linkedin": {
                    "handle": "in/alexmaccaw"
                }
            }
        })
    }
]

def add_api_config_if_not_exists(api_data):
    """Add API configuration if it doesn't already exist"""
    existing = APIConfiguration.query.filter_by(api_name=api_data["api_name"]).first()
    if existing:
        print(f"API '{api_data['api_name']}' already exists.")
        return existing
    
    new_api = APIConfiguration(
        api_name=api_data["api_name"],
        api_url=api_data["api_url"],
        api_key_env=api_data["api_key_env"],
        description=api_data["description"],
        endpoints=api_data["endpoints"],
        format=api_data["format"]
    )
    
    db.session.add(new_api)
    db.session.commit()
    print(f"Added API: {api_data['api_name']}")
    return new_api

def main():
    print("Populating APIs in the database...")
    with app.app_context():
        for api_data in APIS:
            add_api_config_if_not_exists(api_data)
    print("Done.")

if __name__ == "__main__":
    main()