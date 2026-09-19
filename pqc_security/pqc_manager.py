"""
Post-Quantum Cryptography (PQC) Security Manager
Provides end-to-end integration of CRYSTALS-Kyber and CRYSTALS-Dilithium for federated learning payloads:
1. Hospital Node signs updates with Dilithium (Authenticity & Non-repudiation)
2. Hospital Node encrypts update tensors with Kyber KEM + AES-256-GCM (Quantum Confidentiality)
3. Server verifies Dilithium signature and decrypts with Kyber secret key before FedAvg aggregation.
"""

import json
import base64
import hashlib
import time
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict

from .kyber_engine import KyberKEM, KyberKeyPair, KyberCiphertext
from .dilithium_signer import DilithiumSigner, DilithiumKeyPair, DilithiumSignature


@dataclass
class SecurePayload:
    sender_id: str
    recipient_id: str
    round_number: int
    timestamp: float
    kyber_ciphertext: Dict[str, str]
    dilithium_signature: Dict[str, str]
    quantum_security_level: str = "NIST Level 3 (Kyber-768 + Dilithium3)"

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "SecurePayload":
        data = json.loads(json_str)
        return cls(**data)


class PQCManager:
    """
    Unified manager handling all PQC cryptographic operations for the Federated Healthcare Network.
    """

    def __init__(self, kyber_variant: str = "Kyber-768", dilithium_variant: str = "Dilithium3"):
        self.kyber = KyberKEM(variant=kyber_variant)
        self.dilithium = DilithiumSigner(variant=dilithium_variant)
        self.security_level_label = f"NIST Level 3 ({kyber_variant} + {dilithium_variant})"

    def generate_hospital_identity(self, hospital_id: str) -> Tuple[DilithiumKeyPair, KyberKeyPair]:
        """Generates Dilithium signing keys and Kyber encryption keys for a hospital node."""
        dilithium_kp = self.dilithium.generate_keypair(signer_id=hospital_id)
        kyber_kp = self.kyber.generate_keypair()
        return dilithium_kp, kyber_kp

    def generate_server_identity(self) -> Tuple[DilithiumKeyPair, KyberKeyPair]:
        """Generates server PQC keypairs."""
        dilithium_kp = self.dilithium.generate_keypair(signer_id="central_federated_server")
        kyber_kp = self.kyber.generate_keypair()
        return dilithium_kp, kyber_kp

    def package_secure_update(
        self,
        weights_dict: Dict[str, Any],
        sender_id: str,
        sender_dilithium_sk: bytes,
        server_kyber_pk: bytes,
        round_number: int = 1
    ) -> SecurePayload:
        """
        Prepares a quantum-encrypted and digitally signed model update payload to send to the central server.
        Follows Encrypt-then-Sign paradigm: Encrypts update first, then signs ciphertext envelope.
        """
        # 1. Serialize weights
        payload_bytes = json.dumps(weights_dict).encode("utf-8")
        
        # 2. Encrypt raw weights using CRYSTALS-Kyber KEM + AES-256-GCM
        kyber_ct = self.kyber.encrypt_payload(payload_bytes, server_kyber_pk)

        # 3. Digitally sign encrypted package (Encrypt-then-Sign) to prevent oracle attacks
        # Preimage binds: Ciphertext, Nonce, KEM Ciphertext, Sender ID, Round Number
        sig_preimage = (
            kyber_ct.encrypted_payload +
            kyber_ct.nonce +
            kyber_ct.kem_ciphertext +
            sender_id.encode("utf-8") +
            str(round_number).encode("utf-8")
        )
        payload_hash = hashlib.sha3_256(sig_preimage).digest()
        signature = self.dilithium.sign(payload_hash, sender_dilithium_sk, signer_id=sender_id)

        return SecurePayload(
            sender_id=sender_id,
            recipient_id="central_federated_server",
            round_number=round_number,
            timestamp=time.time(),
            kyber_ciphertext=kyber_ct.to_dict(),
            dilithium_signature=signature.to_dict(),
            quantum_security_level=self.security_level_label
        )

    def unpack_and_verify_update(
        self,
        secure_payload: SecurePayload,
        server_kyber_sk: bytes,
        sender_dilithium_pk: bytes
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Verifies sender signature and decrypts weights at the server side.
        CRITICAL: Verifies Dilithium signature BEFORE decrypting to prevent unauthenticated oracle attacks.
        Returns: (is_valid, weights_dict, status_message)
        """
        try:
            kyber_ct = KyberCiphertext.from_dict(secure_payload.kyber_ciphertext)

            # 1. Verify Dilithium signature over ciphertext envelope FIRST
            sig_preimage = (
                kyber_ct.encrypted_payload +
                kyber_ct.nonce +
                kyber_ct.kem_ciphertext +
                secure_payload.sender_id.encode("utf-8") +
                str(secure_payload.round_number).encode("utf-8")
            )
            payload_hash = hashlib.sha3_256(sig_preimage).digest()
            sig = DilithiumSignature.from_dict(secure_payload.dilithium_signature)
            is_sig_valid = self.dilithium.verify(payload_hash, sig, sender_dilithium_pk)
            
            if not is_sig_valid:
                return False, None, f"Dilithium signature verification failed for sender {secure_payload.sender_id}"

            # 2. Decrypt payload using Kyber KEM secret key only after signature verification
            decrypted_bytes = self.kyber.decrypt_payload(kyber_ct, server_kyber_sk)

            # 3. Deserialize weights
            weights = json.loads(decrypted_bytes.decode("utf-8"))
            return True, weights, "Successfully verified Dilithium signature & decrypted Kyber ciphertext"
        except Exception as e:
            return False, None, f"Decryption/Verification Error: {str(e)}"
