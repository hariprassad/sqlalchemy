from sqlalchemy import inspect
from sqlalchemy.future import select as future_select
from sqlalchemy.orm import aliased
from sqlalchemy.orm import defaultload
from sqlalchemy.orm import defer
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Load
from sqlalchemy.orm import Session
from sqlalchemy.orm import subqueryload
from sqlalchemy.orm import with_polymorphic
from sqlalchemy.sql.base import CacheableOptions
from sqlalchemy.sql.visitors import InternalTraversal
from sqlalchemy.testing import eq_
from test.orm import _fixtures
from .inheritance import _poly_fixtures
from ..sql.test_compare import CacheKeyFixture


def stmt_20(*elements):
    return tuple(elem._statement_20() for elem in elements)


class CacheKeyTest(CacheKeyFixture, _fixtures.FixtureTest):
    run_setup_mappers = "once"
    run_inserts = None
    run_deletes = None

    @classmethod
    def setup_mappers(cls):
        cls._setup_stock_mapping()

    def test_mapper_and_aliased(self):
        User, Address, Keyword = self.classes("User", "Address", "Keyword")

        self._run_cache_key_fixture(
            lambda: (inspect(User), inspect(Address), inspect(aliased(User))),
            compare_values=True,
        )

    def test_attributes(self):
        User, Address, Keyword = self.classes("User", "Address", "Keyword")

        self._run_cache_key_fixture(
            lambda: (
                User.id,
                Address.id,
                aliased(User).id,
                aliased(User, name="foo").id,
                aliased(User, name="bar").id,
                User.name,
                User.addresses,
                Address.email_address,
                aliased(User).addresses,
            ),
            compare_values=True,
        )

    def test_unbound_options(self):
        User, Address, Keyword, Order, Item = self.classes(
            "User", "Address", "Keyword", "Order", "Item"
        )

        self._run_cache_key_fixture(
            lambda: (
                joinedload(User.addresses),
                joinedload(User.addresses.of_type(aliased(Address))),
                joinedload("addresses"),
                joinedload(User.orders).selectinload("items"),
                joinedload(User.orders).selectinload(Order.items),
                defer(User.id),
                defer("id"),
                defer("*"),
                defer(Address.id),
                joinedload(User.addresses).defer(Address.id),
                joinedload(aliased(User).addresses).defer(Address.id),
                joinedload(User.addresses).defer("id"),
                joinedload(User.orders).joinedload(Order.items),
                joinedload(User.orders).subqueryload(Order.items),
                subqueryload(User.orders).subqueryload(Order.items),
                subqueryload(User.orders)
                .subqueryload(Order.items)
                .defer(Item.description),
                defaultload(User.orders).defaultload(Order.items),
                defaultload(User.orders),
            ),
            compare_values=True,
        )

    def test_bound_options(self):
        User, Address, Keyword, Order, Item = self.classes(
            "User", "Address", "Keyword", "Order", "Item"
        )

        self._run_cache_key_fixture(
            lambda: (
                Load(User).joinedload(User.addresses),
                Load(User).joinedload(
                    User.addresses.of_type(aliased(Address))
                ),
                Load(User).joinedload(User.orders),
                Load(User).defer(User.id),
                Load(User).subqueryload("addresses"),
                Load(Address).defer("id"),
                Load(Address).defer("*"),
                Load(aliased(Address)).defer("id"),
                Load(User).joinedload(User.addresses).defer(Address.id),
                Load(User).joinedload(User.orders).joinedload(Order.items),
                Load(User).joinedload(User.orders).subqueryload(Order.items),
                Load(User).subqueryload(User.orders).subqueryload(Order.items),
                Load(User)
                .subqueryload(User.orders)
                .subqueryload(Order.items)
                .defer(Item.description),
                Load(User).defaultload(User.orders).defaultload(Order.items),
                Load(User).defaultload(User.orders),
                Load(Address).raiseload("*"),
                Load(Address).raiseload("user"),
            ),
            compare_values=True,
        )

    def test_bound_options_equiv_on_strname(self):
        """Bound loader options resolve on string name so test that the cache
        key for the string version matches the resolved version.

        """
        User, Address, Keyword, Order, Item = self.classes(
            "User", "Address", "Keyword", "Order", "Item"
        )

        for left, right in [
            (Load(User).defer(User.id), Load(User).defer("id")),
            (
                Load(User).joinedload(User.addresses),
                Load(User).joinedload("addresses"),
            ),
            (
                Load(User).joinedload(User.orders).joinedload(Order.items),
                Load(User).joinedload("orders").joinedload("items"),
            ),
        ]:
            eq_(left._generate_cache_key(), right._generate_cache_key())

    def test_future_selects_w_orm_joins(self):

        User, Address, Keyword, Order, Item = self.classes(
            "User", "Address", "Keyword", "Order", "Item"
        )

        a1 = aliased(Address)

        self._run_cache_key_fixture(
            lambda: (
                future_select(User).join(User.addresses),
                future_select(User).join(User.orders),
                future_select(User).join(User.addresses).join(User.orders),
                future_select(User).join(Address, User.addresses),
                future_select(User).join(a1, User.addresses),
                future_select(User).join(User.addresses.of_type(a1)),
                future_select(User)
                .join(Address, User.addresses)
                .join_from(User, Order),
                future_select(User)
                .join(Address, User.addresses)
                .join_from(User, User.orders),
            ),
            compare_values=True,
        )

    def test_orm_query_basic(self):

        User, Address, Keyword, Order, Item = self.classes(
            "User", "Address", "Keyword", "Order", "Item"
        )

        a1 = aliased(Address)

        self._run_cache_key_fixture(
            lambda: stmt_20(
                Session().query(User),
                Session().query(User).prefix_with("foo"),
                Session().query(User).filter_by(name="ed"),
                Session().query(User).filter_by(name="ed").order_by(User.id),
                Session().query(User).filter_by(name="ed").order_by(User.name),
                Session().query(User).filter_by(name="ed").group_by(User.id),
                Session()
                .query(User)
                .join(User.addresses)
                .filter(User.name == "ed"),
                Session().query(User).join(User.orders),
                Session()
                .query(User)
                .join(User.orders)
                .filter(Order.description == "adsf"),
                Session().query(User).join(User.addresses).join(User.orders),
                Session().query(User).join(Address, User.addresses),
                Session().query(User).join(a1, User.addresses),
                Session().query(User).join(User.addresses.of_type(a1)),
                Session().query(Address).join(Address.user),
                Session().query(User, Address).filter_by(name="ed"),
                Session().query(User, a1).filter_by(name="ed"),
            ),
            compare_values=True,
        )

    def test_options(self):
        class MyOpt(CacheableOptions):
            _cache_key_traversal = [
                ("x", InternalTraversal.dp_plain_obj),
                ("y", InternalTraversal.dp_plain_obj),
            ]
            x = 5
            y = ()

        self._run_cache_key_fixture(
            lambda: (
                MyOpt,
                MyOpt + {"x": 10},
                MyOpt + {"x": 15, "y": ("foo",)},
                MyOpt + {"x": 15, "y": ("foo",)} + {"y": ("foo", "bar")},
            ),
            compare_values=True,
        )


class PolyCacheKeyTest(CacheKeyFixture, _poly_fixtures._Polymorphic):
    run_setup_mappers = "once"
    run_inserts = None
    run_deletes = None

    def test_wp_objects(self):
        Person, Manager, Engineer, Boss = self.classes(
            "Person", "Manager", "Engineer", "Boss"
        )

        self._run_cache_key_fixture(
            lambda: (
                inspect(with_polymorphic(Person, [Manager, Engineer])),
                inspect(with_polymorphic(Person, [Manager])),
                inspect(with_polymorphic(Person, [Manager, Engineer, Boss])),
                inspect(
                    with_polymorphic(Person, [Manager, Engineer], flat=True)
                ),
                inspect(
                    with_polymorphic(
                        Person,
                        [Manager, Engineer],
                        future_select(Person)
                        .outerjoin(Manager)
                        .outerjoin(Engineer)
                        .subquery(),
                    )
                ),
            ),
            compare_values=True,
        )

    def test_wp_queries(self):
        Person, Manager, Engineer, Boss = self.classes(
            "Person", "Manager", "Engineer", "Boss"
        )

        def one():
            return (
                Session().query(Person).with_polymorphic([Manager, Engineer])
            )

        def two():
            wp = with_polymorphic(Person, [Manager, Engineer])

            return Session().query(wp)

        def three():
            wp = with_polymorphic(Person, [Manager, Engineer])

            return Session().query(wp).filter(wp.name == "asdfo")

        def three_a():
            wp = with_polymorphic(Person, [Manager, Engineer], flat=True)

            return Session().query(wp).filter(wp.name == "asdfo")

        def four():
            return (
                Session()
                .query(Person)
                .with_polymorphic([Manager, Engineer])
                .filter(Person.name == "asdf")
            )

        def five():
            subq = (
                future_select(Person)
                .outerjoin(Manager)
                .outerjoin(Engineer)
                .subquery()
            )
            wp = with_polymorphic(Person, [Manager, Engineer], subq)

            return Session().query(wp).filter(wp.name == "asdfo")

        def six():
            subq = (
                future_select(Person)
                .outerjoin(Manager)
                .outerjoin(Engineer)
                .subquery()
            )

            return (
                Session()
                .query(Person)
                .with_polymorphic([Manager, Engineer], subq)
                .filter(Person.name == "asdfo")
            )

        self._run_cache_key_fixture(
            lambda: stmt_20(
                one(), two(), three(), three_a(), four(), five(), six()
            ),
            compare_values=True,
        )

    def test_wp_joins(self):
        Company, Person, Manager, Engineer, Boss = self.classes(
            "Company", "Person", "Manager", "Engineer", "Boss"
        )

        def one():
            return (
                Session()
                .query(Company)
                .join(Company.employees)
                .filter(Person.name == "asdf")
            )

        def two():
            wp = with_polymorphic(Person, [Manager, Engineer])
            return (
                Session()
                .query(Company)
                .join(Company.employees.of_type(wp))
                .filter(wp.name == "asdf")
            )

        def three():
            wp = with_polymorphic(Person, [Manager, Engineer])
            return (
                Session()
                .query(Company)
                .join(Company.employees.of_type(wp))
                .filter(wp.Engineer.name == "asdf")
            )

        self._run_cache_key_fixture(
            lambda: stmt_20(one(), two(), three()), compare_values=True,
        )