from jinja2 import nodes
from jinja2.ext import Extension

import caching.base


class FragmentCacheExtension(Extension):
    """
    Cache a chunk of template code based on a queryset.  Since looping over
    querysets is the slowest thing we do, you should wrap you for loop with the
    cache tag.  Uses the default timeout unless you pass a second argument.

    {% cache queryset[, timeout] %}
      ...template code...
    {% endcache %}

    Derived from the jinja2 documentation example.
    """
    tags = set(['cache'])

    def __init__(self, environment):
        super(FragmentCacheExtension, self).__init__(environment)

    def preprocess(self, source, name, filename=None):
        self.name = filename or name
        return source

    def parse(self, parser):
        # the first token is the token that started the tag.  In our case
        # we only listen to ``'cache'`` so this will be a name token with
        # `cache` as value.  We get the line number so that we can give
        # that line number to the nodes we create by hand.
        lineno = parser.stream.next().lineno

        # Use the filename and queryset for the cache key.
        args = [nodes.Const(self.name), parser.parse_expression()]

        # If there is a comma, the user provided a timeout.  If not use
        # None as second parameter.
        if parser.stream.skip_if('comma'):
            args.append(parser.parse_expression())
        else:
            args.append(nodes.Const(None))

        # now we parse the body of the cache block up to `endcache` and
        # drop the needle (which would always be `endcache` in that case)
        body = parser.parse_statements(['name:endcache'], drop_needle=True)

        # now return a `CallBlock` node that calls our _cache_support
        # helper method on this extension.
        return nodes.CallBlock(self.call_method('_cache_support', args),
                               [], [], body).set_lineno(lineno)

    def _cache_support(self, name, queryset, timeout, caller):
        """Cache helper callback."""
        key = 'fragment:%s:%s' % (name, queryset.query_key())
        # Matches the key made in cached().
        flush = caching.base.make_key('f:%s' % key)
        caching.base.add_to_flush_list([queryset.flush_key()], flush)
        return caching.base.cached(caller, key, timeout)


# Nice import name.
cache = FragmentCacheExtension