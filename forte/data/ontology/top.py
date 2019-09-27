from abc import abstractmethod, ABC
from functools import total_ordering
from typing import (
    Iterable, Optional, Set, Tuple, Type, Hashable, Union
)
import numpy as np

from forte.common.exception import IncompleteEntryError
from forte.data.container import EntryContainer
from forte.utils import get_class_name, get_full_module_name

__all__ = [
    "Span",
    "Entry",
    "Annotation",
    "BaseGroup",
    "MultiPackGroup",
    "Group",
    "BaseLink",
    "Link",
    "MultiPackLink",
    "SubEntry",
    "SinglePackEntries",
    "MultiPackEntries",
    "Group",
    "Query"
]


@total_ordering
class Span:
    """
    A class recording the span of annotations. :class:`Span` objects could
    be totally ordered according to their :attr:`begin` as the first sort key
    and :attr:`end` as the second sort key.
    """

    def __init__(self, begin: int, end: int):
        self.begin = begin
        self.end = end

    def __lt__(self, other):
        if self.begin == other.begin:
            return self.end < other.end
        return self.begin < other.begin

    def __eq__(self, other):
        return (self.begin, self.end) == (other.begin, other.end)


class Indexable(ABC):
    """
    A class that implement this would be indexable within the pack it lives in.
    """

    @property
    def index_key(self) -> Hashable:
        raise NotImplementedError


class Entry(Indexable):
    """
    The base class inherited by all NLP entries.
    There will be some associated attributes for each entry.
    - component: specify the creator of the entry
    - _data_pack: each entry can be attached to a pack with
        ``attach`` function.
    - _tid: a unique identifier of this entry in the data pack
    """

    def __init__(self, pack: EntryContainer):
        super(Entry, self).__init__()

        self._tid: str

        self.__component: str
        self.__modified_fields: Set[str] = set()

        # The Entry should have a reference to the data pack, and the data pack
        # need to store the entries. In order to resolve the cyclic references,
        # we create a generic class EntryContainer to be the place holder of
        # the actual. Whether this entry can be added to the pack is delegated
        # to be checked by the pack.
        self.__pack: EntryContainer = pack
        pack.validate(self)

    @property
    def tid(self):
        return self._tid

    @property
    def component(self):
        return self.__component

    def set_component(self, component: str):
        """
        Set the component of the creator of this entry.
        Args:
            component: The component name of the creator (processor or reader).

        Returns:

        """
        self.__component = component

    def set_tid(self, tid: str):
        """
        Set the entry tid.
        Args:
            tid: The entry tid.

        Returns:

        """
        self._tid = f"{get_full_module_name(self)}.{tid}"

    @property
    def pack(self) -> EntryContainer:
        return self.__pack

    def set_fields(self, **kwargs):
        """Set other entry fields"""
        for field_name, field_value in kwargs.items():
            if not hasattr(self, field_name):
                raise AttributeError(
                    f"class {get_class_name(self)} "
                    f"has no attribute {field_name}"
                )
            setattr(self, field_name, field_value)
            self.__modified_fields.add(field_name)

    def __eq__(self, other):
        if other is None:
            return False

        return (type(self), self._tid) == (type(other), other.tid)

    def __hash__(self) -> int:
        return hash((type(self), self._tid))

    @property
    def index_key(self) -> Hashable:
        return self._tid


# EntryType = TypeVar('EntryType', bound=Entry)


@total_ordering
class Annotation(Entry):
    """Annotation type entries, such as "token", "entity mention" and
    "sentence". Each annotation has a text span corresponding to its offset
    in the text.
    """

    def __init__(self, pack: EntryContainer, begin: int, end: int):
        super().__init__(pack)
        self._span = Span(begin, end)

    @property
    def span(self):
        return self._span

    def set_span(self, begin: int, end: int):
        self._span = Span(begin, end)

    def __hash__(self):
        return hash(
            (type(self), self.pack, self.span.begin, self.span.end)
        )

    def __eq__(self, other):
        if other is None:
            return False
        return (type(self), self.span.begin, self.span.end) == \
               (type(other), other.span.begin, other.span.end)

    def __lt__(self, other):
        """
        Have to support total ordering and be consistent with
        __eq__(self, other)
        """
        if self.span != other.span:
            return self.span < other.span
        return str(type(self)) < str(type(other))

    @property
    def text(self):
        if self.pack is None:
            raise ValueError(f"Cannot get text because annotation is not "
                             f"attached to any data pack.")
        return self.pack.text[self.span.begin: self.span.end]

    @property
    def index_key(self) -> str:
        return self.tid


class BaseLink(Entry, ABC):
    def __init__(
            self,
            pack: EntryContainer,
            parent: Optional[Entry] = None,
            child: Optional[Entry] = None
    ):
        super().__init__(pack)

        if parent is not None:
            self.set_parent(parent)
        if child is not None:
            self.set_child(child)

    @abstractmethod
    def set_parent(self, parent: Entry):
        """
        This will set the `parent` of the current instance with given Entry
        The parent is saved internally by its pack specific index key.

        Args:
            parent: The parent entry.

        Returns:

        """
        raise NotImplementedError

    @abstractmethod
    def set_child(self, child: Entry):
        """
        This will set the `child` of the current instance with given Entry
        The child is saved internally by its pack specific index key.

        Args:
            child: The child entry

        Returns:

        """
        raise NotImplementedError

    @abstractmethod
    def get_parent(self) -> Entry:
        """
        Get the parent entry of the link.

        Returns:
             An instance of :class:`Entry` that is the child of the link
             from the given DataPack
        """
        raise NotImplementedError

    @abstractmethod
    def get_child(self) -> Entry:
        """
        Get the child entry of the link.

        Returns:
             An instance of :class:`Entry` that is the child of the link
             from the given DataPack
        """
        raise NotImplementedError

    def __eq__(self, other):
        if other is None:
            return False
        return (type(self), self.get_parent(), self.get_child()) == \
               (type(other), other.get_parent(), other.get_child())

    def __hash__(self):
        return hash((type(self), self.get_parent(), self.get_child()))

    @property
    def index_key(self) -> str:
        return self.tid


class Link(BaseLink):
    """
    The Link type entry connects two entries, such as "dependency link", which
    connect two words and specifies its dependency label.  Each link has a
    parent node and a child node.
    """
    ParentType: Type[Entry]
    ChildType: Type[Entry]

    def __init__(
            self,
            pack: EntryContainer,
            parent: Optional[Entry] = None,
            child: Optional[Entry] = None
    ):
        self._parent: Optional[str] = None
        self._child: Optional[str] = None
        super().__init__(pack, parent, child)

    # TODO: Can we get better type hint here?
    def set_parent(self, parent: Entry):
        """
        This will set the `parent` of the current instance with given Entry
        The parent is saved internally by its pack specific index key.

        Args:
            parent: The parent entry.

        Returns:

        """
        if not isinstance(parent, self.ParentType):
            raise TypeError(
                f"The parent of {type(self)} should be an "
                f"instance of {self.ParentType}, but get {type(parent)}")
        self._parent = parent.tid

    def set_child(self, child: Entry):
        """
       This will set the `child` of the current instance with given Entry
       The child is saved internally by its pack specific index key.

       Args:
           child: The child entry

        Args:
            child:

        Returns:

        """
        if not isinstance(child, self.ChildType):
            raise TypeError(
                f"The parent of {type(self)} should be an "
                f"instance of {self.ParentType}, but get {type(child)}")
        self._child = child.tid

    @property
    def parent(self):
        """
        tid of the parent node. To get the object of the parent node, call
        :meth:`get_parent`.
        """
        return self._parent

    @property
    def child(self):
        """
        tid of the child node. To get the object of the child node, call
        :meth:`get_child`.
        """
        return self._child

    def get_parent(self) -> Entry:
        """
        Get the parent entry of the link.

        Returns:
             An instance of :class:`Entry` that is the parent of the link.
        """
        if self.pack is None:
            raise ValueError(f"Cannot get parent because link is not "
                             f"attached to any data pack.")
        return self.pack.get_entry(self._parent)

    def get_child(self) -> Entry:
        """
        Get the child entry of the link.

        Returns:
             An instance of :class:`Entry` that is the child of the link.
        """
        if self.pack is None:
            raise ValueError(f"Cannot get child because link is not"
                             f" attached to any data pack.")
        return self.pack.get_entry(self._child)


class BaseGroup(Entry):
    """
    Group is an entry that represent a group of other entries. For example,
    a "coreference group" is a group of coreferential entities. Each group will
    store a set of members, no duplications allowed.

    This is the BaseGroup interface. Specific member constraints are defined
    in the inherited classes.
    """
    member_type: Type[Entry]

    def __init__(
            self,
            pack: EntryContainer,
            members: Optional[Set[Entry]] = None,
    ):
        super().__init__(pack)

        # Store the group member's id.
        self._members: Set[str] = set()
        if members is not None:
            self.add_members(members)

    def add_member(self, member: Entry):
        """
        Add one entry to the group.
        Args:
            member:

        Returns:

        """
        self.add_members([member])

    def add_members(self, members: Iterable[Entry]):
        """
        Add members to the group.

        Args:
            members: An iterator of members to be added to the group.

        Returns:

        """
        for member in members:
            if not isinstance(member, self.member_type):
                raise TypeError(
                    f"The members of {type(self)} should be "
                    f"instances of {self.member_type}, but get {type(member)}")

            self._members.add(member.tid)

    @property
    def members(self):
        """
        A list of member tids. To get the member objects, call
        :meth:`get_members` instead.
        :return:
        """
        return self._members

    def __hash__(self):
        return hash((type(self), tuple(self.members)))

    def __eq__(self, other):
        if other is None:
            return False
        return (type(self), self.members) == (type(other), other.members)

    def get_members(self):
        """
        Get the member entries in the group.

        Returns:
             An set of instances of :class:`Entry` that are the members of the
             group.
        """
        if self.pack is None:
            raise ValueError(f"Cannot get members because group is not "
                             f"attached to any data pack.")
        member_entries = set()
        for m in self.members:
            member_entries.add(self.pack.get_entry(m))
        return member_entries

    @property
    def index_key(self) -> str:
        return self.tid


class Group(BaseGroup):
    """
    Group is an entry that represent a group of other entries. For example,
    a "coreference group" is a group of coreferential entities. Each group will
    store a set of members, no duplications allowed.
    """
    member_type: Type[Entry] = Entry


class SubEntry(Entry):
    """
    This is used to identify an Entry in one of the packs in the Multipack.
    For example, the sentence in one of the packs. A pack_index and an entry
    is needed to identify this.

    Args:
        pack_index: Indicate which pack this entry belongs. If this is less
        than 0, then this is a cross pack entry.
        entry_id: The tid of the entry in the sub pack.
    """

    def __init__(self, pack: EntryContainer, pack_index: int, entry_id: str):
        super().__init__(pack)
        self._pack_index: int = pack_index
        self._entry_id: str = entry_id

    @property
    def pack_index(self):
        return self._pack_index

    @property
    def entry_id(self):
        return self._entry_id

    def __hash__(self):
        return hash((type(self), self._pack_index, self._entry_id))

    def __eq__(self, other):
        if other is None:
            return False
        return (type(self), self.pack_index, self.entry_id
                ) == (type(other), other.pack_index, other.entry)

    @property
    def index_key(self) -> Tuple[int, str]:
        return self._pack_index, self._entry_id


class MultiPackLink(BaseLink):
    """
    The MultiPackLink are used to link entries in a MultiPack, which is designed
    to support cross pack linking, this can support applications such as
    sentence alignment and cross-document coreference. Each link should have
    a parent node and a child node. Note that the nodes are SubEntry(s), thus
    have one additional index on which pack it comes from.
    """

    ParentType: Type[SubEntry]
    ChildType: Type[SubEntry]

    def __init__(
            self,
            pack: EntryContainer,
            parent: Optional[SubEntry],
            child: Optional[SubEntry],
    ):
        """

        Args:
            parent: The parent of the link, it should be a tuple of the name and
            an entry.
            child:
        """
        super().__init__(pack, parent, child)

        self._parent: Optional[Tuple[int, str]] = None
        self._child: Optional[Tuple[int, str]] = None

        if parent is not None:
            self.set_parent(parent)
        if child is not None:
            self.set_child(child)

    @property
    def parent(self) -> Tuple[int, str]:
        if self._parent is None:
            raise IncompleteEntryError("Parent is not set for this link.")
        return self._parent

    @property
    def child(self) -> Tuple[int, str]:
        if self._child is None:
            raise IncompleteEntryError("Child is not set for this link.")
        return self._child

    def set_parent(self, parent: SubEntry):  # type: ignore
        """
        This will set the `parent` of the current instance with given Entry
        The parent is saved internally as a tuple: pack_name and entry.tid

        Args:
            parent: The parent of the link, identified as a sub entry, which
            has a value for the pack index and the tid in the pack.

        Returns:

        """
        if not isinstance(parent, self.ParentType):
            raise TypeError(
                f"The parent of {type(self)} should be an "
                f"instance of {self.ParentType}, but get {type(parent)}")
        self._parent = parent.index_key

    def set_child(self, child: SubEntry):  # type: ignore
        if not isinstance(child, self.ChildType):
            raise TypeError(
                f"The parent of {type(self)} should be an "
                f"instance of {self.ChildType}, but get {type(child)}")
        self._child = child.index_key

    def get_parent(self) -> SubEntry:
        """
        Get the parent entry of the link.

        Returns:
             An instance of :class:`SubEntry` that is the parent of the link
             from the given DataPack.
        """
        if self._parent is None:
            raise IncompleteEntryError("The parent of this link is not set.")
        pack_idx, parent_tid = self._parent

        return SubEntry(self.pack, pack_idx, parent_tid)

    def get_child(self) -> SubEntry:
        """
        Get the child entry of the link.

        Returns:
             An instance of :class:`SubEntry` that is the child of the link
             from the given DataPack.
        """
        if self._child is None:
            raise IncompleteEntryError("The parent of this link is not set.")

        pack_idx, child_tid = self._child

        return SubEntry(self.pack, pack_idx, child_tid)


class MultiPackGroup(BaseGroup):
    """
    Group type entries, such as "coreference group". Each group has a set
    of members.
    """

    def __init__(
            self,
            pack: EntryContainer,
            members: Optional[Set[SubEntry]],
    ):
        super().__init__(pack, members)


SinglePackEntries = (Link, Group, Annotation)
MultiPackEntries = (MultiPackLink, MultiPackGroup)


class Query(Entry):
    def __init__(self, query: Union[np.ndarray, str]):
        super().__init__()
        self.query: Union[np.ndarray, str] = query

    def hash(self):
        if isinstance(self.query, np.ndarray):
            return hash(self.query.tobytes())
        else:
            return hash(self.query)

    def eq(self, other: 'Query') -> bool:
        if isinstance(self.query, str):
            if not isinstance(self.query, str):
                return False
            else:
                return self.query == other.query
        else:
            if not isinstance(self.query, np.ndarray):
                return False
            else:
                return np.all(self.query == other.query)
