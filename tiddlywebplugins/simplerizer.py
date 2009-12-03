"""
TiddlyWeb serializer base class.
"""

from tiddlyweb.model.bag import Bag
from tiddlyweb.model.policy import Policy
from tiddlyweb.serializations import SerializationInterface

__version__ = "0.1"
 
class Simplerization(SerializationInterface):
    """Access TiddlyWeb resources using a generic representation."""

    def dump(self, object):
        """Dumps a dictionary object to a string."""
        raise NoSerializationError

    def load(self, input_string):
        """Loads a dictionary object from a string."""
        raise NoSerializationError

    def __init__(self, environ=None):
        SerializationInterface.__init__(self, environ)
        self._bag_perms_cache = {}

    def list_recipes(self, recipes):
        """Creates representation of a list of recipe names."""
        return self.dump([recipe.name for recipe in recipes])

    def list_bags(self, bags):
        """Creates representation of a list of bag names."""
        return self.dump([bag.name for bag in bags])

    def list_tiddlers(self, bag):
        """Creates representation of the list of tiddlers in a bag."""
        return self.dump([self._tiddler_dict(tiddler) for
            tiddler in bag.gen_tiddlers()])

    def recipe_as(self, recipe):
        """Creates representation of a recipe."""
        policy_dict = self._get_policy(recipe)
        info = dict(desc=recipe.desc, policy=policy_dict, recipe=recipe.get_recipe())
        return self.dump(info)

    def tiddler_as(self, tiddler):
        tiddler_dict = self._tiddler_dict(tiddler)
        if (tiddler.type and tiddler.type != 'None' and not
                tiddler.type.startswith('text/')):
            tiddler_dict['text'] = b64encode(tiddler.text)
        else:
            tiddler_dict['text'] = tiddler.text
        return self.dump(tiddler_dict)

    def bag_as(self, bag):
        """Creates representation of a bag."""
        policy_dict = self._get_policy(bag)
        info = dict(desc=bag.desc, policy=policy_dict)
        return self.dump(info)

    def as_recipe(self, recipe, input_string):
        """Creates a recipe from representation."""
        info = self.load(input_string)
        recipe.set_recipe(info.get('recipe', []))
        recipe.desc = info.get('desc', '')
        self._set_policy(info, recipe)
        return recipe

    def as_bag(self, bag, input_string):
        """Creates a bag from a representation."""
        info = self.load(input_string)
        bag.desc = info.get('desc', '')
        self._set_policy(info, bag)
        return bag

    def as_tiddler(self, tiddler, input_string):
        """Creates a tiddler from a representation."""
        dict_from_input = self.load(input_string)
        accepted_keys = ['created', 'modified', 'modifier', 'tags', 'fields',
                'text', 'type']
        for key, value in dict_from_input.iteritems():
            if value is not None and key in accepted_keys:
                setattr(tiddler, key, value)
        if (tiddler.type and tiddler.type != 'None' and not
                tiddler.type.startswith('text/')):
            tiddler.text = b64decode(tiddler.text)
        return tiddler

    def _get_policy(self, item):
        """Creates a bag from a representation."""
        policy = item.policy
        policy_dict = {}
        for key in Policy.attributes:
            policy_dict[key] = getattr(policy, key)
        return policy_dict

    def _set_policy(self, info, item):
        if info.get('policy', {}):
            item.policy = Policy()
            for key, value in info['policy'].items():
                item.policy.__setattr__(key, value)

    def _tiddler_dict(self, tiddler):
        """
        Creates a dictionary of header tiddler fields and values
        under the control of the query_string option 'fat' which 
        when '1' also includes the tiddler content.
        """
        unwanted_keys = ['text', 'store']
        wanted_keys = [attribute for attribute in tiddler.slots if
                attribute not in unwanted_keys]
        wanted_info = {}
        for attribute in wanted_keys:
            wanted_info[attribute] = getattr(tiddler, attribute, None)
        wanted_info['permissions'] = self._tiddler_permissions(tiddler)
        try:
            fat = self.environ['tiddlyweb.query'].get('fat', [None])[0]
            if fat:
                wanted_info['text'] = tiddler.text
        except KeyError:
            pass # tiddlyweb.query is not there
        return dict(wanted_info)

    def _tiddler_permissions(self, tiddler):
        """
        Makes a list of the permissions the current user has
        to access this tiddler.
        """

        def _read_bag_perms(environ, tiddler):
            """
            Reads the permissions for the bag containing
            this tiddler.
            """
            perms = []
            if 'tiddlyweb.usersign' in environ:
                store = tiddler.store
                if store:
                    bag = Bag(tiddler.bag)
                    bag.skinny = True
                    bag = store.get(bag)
                    perms = bag.policy.user_perms(
                            environ['tiddlyweb.usersign'])
            return perms

        bag_name = tiddler.bag
        perms = []
        if len(self._bag_perms_cache):
            if bag_name in self._bag_perms_cache:
                perms = self._bag_perms_cache[bag_name]
            else:
                perms = _read_bag_perms(self.environ, tiddler)
        self._bag_perms_cache[bag_name] = perms
        return perms
