# Copyright (c) 2016-2018, Neil Booth
# Copyright (c) 2018, the ElectrumX authors
#
# All rights reserved.
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''Deserializer for Crown NF special transaction types'''

from collections import namedtuple

from electrumx.lib.tx import DeserializerAuxPow
from electrumx.lib.util import (pack_le_uint16, pack_le_int32, pack_le_uint32,
                                pack_le_int64, pack_varint, pack_varbytes,
                                pack_be_uint16)


class CrownTx(namedtuple("CrownTx",
                        "version inputs outputs locktime "
                        "tx_type extra_payload")):
    '''Class representing a Crown transaction'''
    def serialize(self):
        nLocktime = pack_le_uint32(self.locktime)
        txins = (pack_varint(len(self.inputs)) +
                 b''.join(tx_in.serialize() for tx_in in self.inputs))
        txouts = (pack_varint(len(self.outputs)) +
                  b''.join(tx_out.serialize() for tx_out in self.outputs))

        if self.tx_type:
            uVersion = pack_le_uint16(self.version)
            uTxType = pack_le_uint16(self.tx_type)
            vExtra = self._serialize_extra_payload()
            return uVersion + uTxType + txins + txouts + nLocktime + vExtra
        else:
            nVersion = pack_le_int32(self.version)
            return nVersion + txins + txouts + nLocktime

    def _serialize_extra_payload(self):
        extra = self.extra_payload
        spec_tx_class = DeserializerCrown.SPEC_TX_HANDLERS.get(self.tx_type)
        if not spec_tx_class:
            assert isinstance(extra, (bytes, bytearray))
            return pack_varbytes(extra)

        if not isinstance(extra, spec_tx_class):
            raise ValueError('Crown tx_type does not conform with extra'
                             ' payload class: %s, %s' % (self.tx_type, extra))
        return pack_varbytes(extra.serialize())


class CrownGovernanceVoteTx(namedtuple("CrownGovernanceVoteTx",
                              "voterId electionCode vote candidate keyId signature")):
    '''Class representing Crown Governance Vote Tx'''
    def serialize(self):
        return (
            self.voterId.serialize() + 
            pack_le_int64(self.electionCode) +
            pack_le_int64(self.vote) +
            pack_le_int64(self.candidate) +
            self.keyId +
            pack_varbytes(self.signature)
        )

    @classmethod
    def read_tx_extra(cls, deser):
        return CrownGovernanceVoteTx(
            deser._read_varbytes(),
            deser._read_le_int64(),
            deser._read_le_int64(),
            deser._read_le_int64(),
            deser._read_nbytes(20),
            deser._read_varbytes()
        )


class TxOutPoint(namedtuple("TxOutPoint", "hash index")):
    '''Class representing tx output outpoint'''
    def serialize(self):
        assert len(self.hash) == 32
        return (
            self.hash +                                 # hash
            pack_le_uint32(self.index)                  # index
        )

    @classmethod
    def read_outpoint(cls, deser):
        return TxOutPoint(
            deser._read_nbytes(32),                     # hash
            deser._read_le_uint32()                     # index
        )


class DeserializerCrown(DeserializerAuxPow):
    '''Deserializer for Crown NF special tx types'''
    # Supported Spec Tx types and corresponding classes mapping
    GOVERNANCE_VOTE_TX = 1
    SPEC_TX_HANDLERS = {
        GOVERNANCE_VOTE_TX: CrownGovernanceVoteTx,
    }

    def _read_outpoint(self):
        return TxOutPoint.read_outpoint(self)

    def read_tx(self):
        header = self._read_le_uint32()
        tx_type = header >> 16  # NF tx type
        if tx_type:
            version = header & 0x0000ffff
        else:
            version = header

        if tx_type and version < 3:
            version = header
            tx_type = 0

        inputs = self._read_inputs()
        outputs = self._read_outputs()
        locktime = self._read_le_uint32()
        if tx_type:
            extra_payload_size = self._read_varint()
            end = self.cursor + extra_payload_size
            spec_tx_class = DeserializerCrown.SPEC_TX_HANDLERS.get(tx_type)
            if spec_tx_class:
                read_method = getattr(spec_tx_class, 'read_tx_extra', None)
                extra_payload = read_method(self)
                assert isinstance(extra_payload, spec_tx_class)
            else:
                extra_payload = self._read_nbytes(extra_payload_size)
            assert self.cursor == end
        else:
            extra_payload = b''
        tx = CrownTx(version, inputs, outputs, locktime, tx_type, extra_payload)
        return tx
