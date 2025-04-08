"""
OSINT API Catalog
This module contains a curated list of OSINT APIs with multi-level categorization
to support intelligent API selection by AI based on user input data.

Categorization Structure:
- Level 1 (Data Type): TEXT, IMAGE, VIDEO, LOCATION, NETWORK
- Level 2 (Entity Type): PERSON, ORGANIZATION, DOMAIN, DEVICE, ADDRESS, etc.
- Level 3 (Attribute): NAME, EMAIL, PHONE, IP, URL, FACE, etc.
"""

import json

# A comprehensive set of categorized OSINT APIs for the platform
OSINT_APIS = [
    # TEXT/PERSON/EMAIL APIs
    {
        "api_name": "EmailRep",
        "api_url": "https://emailrep.io",
        "api_key_env": "EMAILREP_API_KEY",
        "description": "EmailRep is a simple API to check email address reputation and provide domain information. It helps identify suspicious or malicious email addresses.\n\nCategories: TEXT/PERSON/EMAIL",
        "endpoints": json.dumps({
            "email_lookup": {
                "path": "/query/{email}",
                "method": "GET",
                "headers": {
                    "Key": "{api_key}"
                },
                "data_type": "TEXT",
                "entity_type": "PERSON",
                "attribute_type": "EMAIL",
                "description": "Get reputation and information for an email address"
            }
        }),
        "format": json.dumps({
            "email": "string",
            "reputation": "string",
            "suspicious": "boolean",
            "references": "integer",
            "details": {
                "blacklisted": "boolean",
                "malicious_activity": "boolean",
                "malicious_activity_recent": "boolean",
                "credentials_leaked": "boolean",
                "credentials_leaked_recent": "boolean",
                "data_breach": "boolean",
                "first_seen": "string",
                "last_seen": "string",
                "domain_exists": "boolean",
                "domain_reputation": "string",
                "new_domain": "boolean",
                "days_since_domain_creation": "integer",
                "suspicious_tld": "boolean",
                "spam": "boolean",
                "free_provider": "boolean",
                "disposable": "boolean",
                "deliverable": "boolean",
                "accept_all": "boolean",
                "valid_mx": "boolean",
                "spoofable": "boolean",
                "spf_strict": "boolean",
                "dmarc_enforced": "boolean",
                "profiles": "array"
            }
        })
    },
    {
        "api_name": "Hunter.io",
        "api_url": "https://api.hunter.io",
        "api_key_env": "HUNTER_API_KEY",
        "description": "Hunter.io allows you to find and verify professional email addresses for domains and companies. Great for business intelligence and corporate investigations.\n\nCategories: TEXT/PERSON/EMAIL, TEXT/ORGANIZATION/DOMAIN",
        "endpoints": json.dumps({
            "domain_search": {
                "path": "/v2/domain-search",
                "method": "GET",
                "params": {
                    "domain": "{domain}",
                    "api_key": "{api_key}"
                },
                "data_type": "TEXT",
                "entity_type": "ORGANIZATION",
                "attribute_type": "DOMAIN",
                "description": "Find email addresses for a domain"
            },
            "email_verifier": {
                "path": "/v2/email-verifier",
                "method": "GET",
                "params": {
                    "email": "{email}",
                    "api_key": "{api_key}"
                },
                "data_type": "TEXT",
                "entity_type": "PERSON",
                "attribute_type": "EMAIL",
                "description": "Verify an email address"
            }
        }),
        "format": json.dumps({
            "data": {
                "domain": "string",
                "disposable": "boolean",
                "webmail": "boolean",
                "emails": "array",
                "pattern": "string"
            },
            "meta": {
                "results": "integer",
                "limit": "integer",
                "offset": "integer",
                "params": "object"
            }
        })
    },
    
    # TEXT/PERSON/PHONE APIs
    {
        "api_name": "Numverify",
        "api_url": "https://numverify.com/api",
        "api_key_env": "NUMVERIFY_API_KEY",
        "description": "Numverify provides global phone number validation and information lookup. It helps verify phone numbers and determine their carrier, location, and line type.\n\nCategories: TEXT/PERSON/PHONE",
        "endpoints": json.dumps({
            "validate": {
                "path": "/validate",
                "method": "GET",
                "params": {
                    "number": "{phone}",
                    "country_code": "{country_code}",
                    "format": "1",
                    "access_key": "{api_key}"
                },
                "data_type": "TEXT",
                "entity_type": "PERSON",
                "attribute_type": "PHONE",
                "description": "Validate a phone number"
            }
        }),
        "format": json.dumps({
            "valid": "boolean",
            "number": "string",
            "local_format": "string",
            "international_format": "string",
            "country_prefix": "string",
            "country_code": "string",
            "country_name": "string",
            "location": "string",
            "carrier": "string",
            "line_type": "string"
        })
    },
    
    # TEXT/PERSON/USERNAME APIs
    {
        "api_name": "Namecheckr",
        "api_url": "https://namecheckr.com/api",
        "api_key_env": "NAMECHECKR_API_KEY",
        "description": "Namecheckr checks username availability across multiple social media platforms and domains. Useful for social media intelligence and profile hunting.\n\nCategories: TEXT/PERSON/USERNAME",
        "endpoints": json.dumps({
            "check_username": {
                "path": "/check",
                "method": "GET",
                "params": {
                    "username": "{username}",
                    "key": "{api_key}"
                },
                "data_type": "TEXT",
                "entity_type": "PERSON",
                "attribute_type": "USERNAME",
                "description": "Check username availability across platforms"
            }
        }),
        "format": json.dumps({
            "username": "string",
            "platforms": {
                "twitter": "boolean",
                "instagram": "boolean",
                "facebook": "boolean",
                "github": "boolean",
                "linkedin": "boolean",
                "reddit": "boolean",
                "pinterest": "boolean"
            }
        })
    },
    
    # NETWORK/DEVICE/IP APIs
    {
        "api_name": "IPinfo",
        "api_url": "https://ipinfo.io",
        "api_key_env": "IPINFO_API_KEY",
        "description": "IPinfo provides accurate IP address data that helps understand and reach targeted audiences. The service offers IP to geolocation, ASN, carrier information, and more.\n\nCategories: NETWORK/DEVICE/IP, LOCATION/ADDRESS/COORDINATES",
        "endpoints": json.dumps({
            "ip_lookup": {
                "path": "/{ip}",
                "method": "GET",
                "params": {
                    "token": "{api_key}"
                },
                "data_type": "NETWORK",
                "entity_type": "DEVICE",
                "attribute_type": "IP",
                "description": "Get details for a specific IP address"
            },
            "bulk_lookup": {
                "path": "/batch",
                "method": "POST",
                "params": {
                    "token": "{api_key}"
                },
                "data_type": "NETWORK",
                "entity_type": "DEVICE",
                "attribute_type": "IP",
                "description": "Look up details for multiple IP addresses"
            }
        }),
        "format": json.dumps({
            "ip": "string",
            "hostname": "string",
            "city": "string",
            "region": "string",
            "country": "string",
            "loc": "string",
            "org": "string",
            "postal": "string",
            "timezone": "string"
        })
    },
    {
        "api_name": "Shodan",
        "api_url": "https://api.shodan.io",
        "api_key_env": "SHODAN_API_KEY",
        "description": "Shodan is a search engine for Internet-connected devices. It allows you to discover which of your devices are connected to the Internet, where they're located, and who's using them.\n\nCategories: NETWORK/DEVICE/IP, NETWORK/DOMAIN/SECURITY",
        "endpoints": json.dumps({
            "host_information": {
                "path": "/shodan/host/{ip}",
                "method": "GET",
                "params": {
                    "key": "{api_key}"
                },
                "data_type": "NETWORK",
                "entity_type": "DEVICE",
                "attribute_type": "IP",
                "description": "Get information for a specific host/IP"
            },
            "dns_resolve": {
                "path": "/dns/resolve",
                "method": "GET",
                "params": {
                    "hostnames": "{domains}",
                    "key": "{api_key}"
                },
                "data_type": "NETWORK",
                "entity_type": "DOMAIN",
                "attribute_type": "HOST",
                "description": "Resolve domain names to IP addresses"
            }
        }),
        "format": json.dumps({
            "ip_str": "string",
            "ports": "array",
            "hostnames": "array",
            "country_code": "string",
            "country_name": "string",
            "city": "string",
            "latitude": "number",
            "longitude": "number",
            "isp": "string",
            "org": "string",
            "data": "array"
        })
    },
    
    # NETWORK/DOMAIN/URL APIs
    {
        "api_name": "VirusTotal",
        "api_url": "https://www.virustotal.com/api/v3",
        "api_key_env": "VIRUSTOTAL_API_KEY",
        "description": "VirusTotal analyzes files and URLs for viruses, worms, trojans, and all kinds of malware. It's a valuable tool for threat intelligence and security research.\n\nCategories: NETWORK/DOMAIN/URL, NETWORK/DEVICE/FILE",
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
                "data_type": "NETWORK",
                "entity_type": "DOMAIN",
                "attribute_type": "URL",
                "description": "Scan a URL for threats"
            },
            "domain_report": {
                "path": "/domains/{domain}",
                "method": "GET",
                "headers": {
                    "x-apikey": "{api_key}"
                },
                "data_type": "NETWORK",
                "entity_type": "DOMAIN",
                "attribute_type": "HOST",
                "description": "Get a domain report"
            }
        }),
        "format": json.dumps({
            "data": {
                "id": "string",
                "type": "string",
                "attributes": {
                    "last_analysis_stats": "object",
                    "last_analysis_results": "object",
                    "reputation": "number",
                    "categories": "object"
                }
            }
        })
    },
    
    # LOCATION/ADDRESS APIs
    {
        "api_name": "Geocoding",
        "api_url": "https://geocode.maps.co",
        "api_key_env": None,
        "description": "Free geocoding API that converts addresses into geographic coordinates and vice versa. Useful for location-based OSINT.\n\nCategories: LOCATION/ADDRESS/COORDINATES",
        "endpoints": json.dumps({
            "forward_geocode": {
                "path": "/search",
                "method": "GET",
                "params": {
                    "q": "{address}",
                    "api_key": "{api_key}"
                },
                "data_type": "LOCATION",
                "entity_type": "ADDRESS",
                "attribute_type": "TEXT",
                "description": "Convert an address to coordinates"
            },
            "reverse_geocode": {
                "path": "/reverse",
                "method": "GET",
                "params": {
                    "lat": "{latitude}",
                    "lon": "{longitude}",
                    "api_key": "{api_key}"
                },
                "data_type": "LOCATION",
                "entity_type": "ADDRESS",
                "attribute_type": "COORDINATES",
                "description": "Convert coordinates to an address"
            }
        }),
        "format": json.dumps({
            "place_id": "number",
            "licence": "string",
            "osm_type": "string",
            "osm_id": "number",
            "lat": "string",
            "lon": "string",
            "display_name": "string",
            "address": {
                "house_number": "string",
                "road": "string",
                "suburb": "string",
                "city": "string",
                "county": "string",
                "state": "string",
                "postcode": "string",
                "country": "string",
                "country_code": "string"
            },
            "boundingbox": "array"
        })
    },
    
    # IMAGE/PERSON/FACE APIs
    {
        "api_name": "FaceCheck",
        "api_url": "https://facecheck.id/api",
        "api_key_env": "FACECHECK_API_KEY",
        "description": "FaceCheck provides facial recognition services to identify people in images. Can be used for identity verification and person search.\n\nCategories: IMAGE/PERSON/FACE",
        "endpoints": json.dumps({
            "face_search": {
                "path": "/search",
                "method": "POST",
                "headers": {
                    "x-api-key": "{api_key}"
                },
                "data": {
                    "image": "{base64_image}"
                },
                "data_type": "IMAGE",
                "entity_type": "PERSON",
                "attribute_type": "FACE",
                "description": "Search for faces in an image"
            }
        }),
        "format": json.dumps({
            "results": "array",
            "face_count": "integer",
            "matches": "array",
            "processing_time": "number"
        })
    },
    
    # IMAGE/DEVICE/LICENSE_PLATE
    {
        "api_name": "PlateRecognizer",
        "api_url": "https://api.platerecognizer.com/v1",
        "api_key_env": "PLATE_RECOGNIZER_API_KEY",
        "description": "PlateRecognizer reads license plates in images. Useful for vehicle identification and tracking in investigations.\n\nCategories: IMAGE/DEVICE/LICENSE_PLATE, TEXT/DEVICE/LICENSE_PLATE",
        "endpoints": json.dumps({
            "plate_reader": {
                "path": "/plate-reader",
                "method": "POST",
                "headers": {
                    "Authorization": "Token {api_key}"
                },
                "data": {
                    "upload": "{image_file}"
                },
                "data_type": "IMAGE",
                "entity_type": "DEVICE",
                "attribute_type": "LICENSE_PLATE",
                "description": "Read license plates from an image"
            }
        }),
        "format": json.dumps({
            "results": [
                {
                    "plate": "string",
                    "confidence": "number",
                    "region": {
                        "code": "string",
                        "score": "number"
                    },
                    "vehicle": {
                        "type": "string",
                        "score": "number"
                    }
                }
            ],
            "processing_time": "number"
        })
    },
    
    # TEXT/ORGANIZATION/DOMAIN
    {
        "api_name": "WhoisXML",
        "api_url": "https://www.whoisxmlapi.com/whoisserver/WhoisService",
        "api_key_env": "WHOISXML_API_KEY",
        "description": "WhoisXML API provides domain WHOIS data, DNS information, domain availability, and more. Essential for domain intelligence.\n\nCategories: TEXT/ORGANIZATION/DOMAIN, NETWORK/DOMAIN/WHOIS",
        "endpoints": json.dumps({
            "whois_lookup": {
                "path": "",
                "method": "GET",
                "params": {
                    "domainName": "{domain}",
                    "apiKey": "{api_key}",
                    "outputFormat": "JSON"
                },
                "data_type": "TEXT",
                "entity_type": "ORGANIZATION",
                "attribute_type": "DOMAIN",
                "description": "Get WHOIS information for a domain"
            }
        }),
        "format": json.dumps({
            "WhoisRecord": {
                "domainName": "string",
                "registryData": {
                    "createdDate": "string",
                    "updatedDate": "string",
                    "expiresDate": "string",
                    "registrant": {
                        "name": "string",
                        "organization": "string",
                        "street1": "string",
                        "city": "string",
                        "state": "string",
                        "postalCode": "string",
                        "country": "string",
                        "email": "string",
                        "telephone": "string"
                    }
                }
            }
        })
    },
    
    # TEXT/PERSON/SOCIAL
    {
        "api_name": "SocialProfiler",
        "api_url": "https://socialprofiler.api/v1",
        "api_key_env": "SOCIALPROFILER_API_KEY",
        "description": "SocialProfiler aggregates social media profiles based on name, email, or username. Good for social media intelligence and profile discovery.\n\nCategories: TEXT/PERSON/SOCIAL, TEXT/PERSON/USERNAME",
        "endpoints": json.dumps({
            "search_by_email": {
                "path": "/search/email",
                "method": "GET",
                "headers": {
                    "Authorization": "Bearer {api_key}"
                },
                "params": {
                    "email": "{email}"
                },
                "data_type": "TEXT",
                "entity_type": "PERSON",
                "attribute_type": "EMAIL",
                "description": "Find social profiles by email"
            },
            "search_by_username": {
                "path": "/search/username",
                "method": "GET",
                "headers": {
                    "Authorization": "Bearer {api_key}"
                },
                "params": {
                    "username": "{username}"
                },
                "data_type": "TEXT",
                "entity_type": "PERSON",
                "attribute_type": "USERNAME",
                "description": "Find social profiles by username"
            }
        }),
        "format": json.dumps({
            "profiles": "array",
            "platforms": "array",
            "total_count": "integer",
            "confidence_score": "number"
        })
    }
]