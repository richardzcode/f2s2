f2s2
====

## Version

0.0.1

## Intro

f2s2, funnel for suck service, is to make sure same requests at one time only hit server once. It is inspired by a complex/expensive CMS. I was very suprised that its caching layer does not prevent same request fall through at the same time. So cache miss on one hot content would potentially crash its content manager. 

Of course Varnish or Nginx etc. can accomplish the job. This is more of a small execise for me on Python.

## Usage

1. Modify config.py. For example
```
{
    'localPort': 8888,
    'remoteHost': 'http://google.com',
}
```
2. Run:
```
python f2s2.py
```
3. Test:
```
ab -n 100 -c 20 http://localhost:8888/
```
