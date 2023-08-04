"""
This module contains tests for lock on removal feature
of GNOME desktop environment.
Most of the tests are parametrized to test both
optional and required smart card in authselect.
All tests depend on SCAutolib GUI module.

If not stated otherwise tests in this module use virtual cards
and share the following setup steps:
    1. Create local CA
    2. Create virtual smart card with certs signed by created CA
    3. Update /etc/sssd/sssd.conf so it contains following fields
        [sssd]
        debug_level = 9
        services = nss, pam,
        domains = shadowutils
        certificate_verification = no_ocsp
        [pam]
        debug_level = 9
        pam_cert_auth = True
        [domain/shadowutils]
        debug_level = 9
        id_provider = files
        [certmap/shadowutils/username]
        matchrule = <SUBJECT>.*CN=username.*
"""

from SCAutolib.models.authselect import Authselect
from SCAutolib.models.gui import GUI, keyboard
from time import sleep
import pytest


@pytest.mark.parametrize("required", [(True), (False)])
def test_lock_on_removal(local_user, required):
    """Local user removes the card while logged in to lock the screen.

    Test steps
        A. Configure SSSD:
            authselect select sssd with-smartcard
            with-smartcard-lock-on-removal [with-smartcard-required]
        B. Start GDM and insert PIN to log in
        C. Remove the smart card
        D. Wake up the system by pressing enter key
            and unlock screen using PIN

    Expected result
        A. Configuration is updated
        B. GDM starts and user logs in successfully
        C. The system locks itself after the card is removed
        D. The system is unlocked
    """

    with Authselect(required=required, lock_on_removal=True), GUI() as gui:
        # insert the card and sign in a standard way
        with local_user.card(insert=True) as card:
            sleep(5)
            gui.assert_text('PIN')
            gui.kb_write(local_user.pin)
            gui.kb_send('enter', wait_time=20)
            # confirm that you are logged in
            gui.assert_text('Activities')

            # remove the card and wait for the screen to lock
            card.remove()
            sleep(5)
            # Locking the screen in GNOME apparently does not generate any log.
            # This could be checked by monitoring D-Bus signals

            # Wake up the black screen by pressing enter
            gui.wake_by_mouse()
            gui.kb_send('enter', screenshot=False)
            # Confirm that the screen is locked
            # After the screen has been locked, there should be no Activities
            gui.assert_no_text('Activities')
            gui.assert_text('insert')

            card.insert()
            gui.kb_write(local_user.pin)
            gui.kb_send('enter', wait_time=20)
            # confirm that you are logged back in
            gui.assert_text('Activities')


def test_lock_on_removal_password(local_user):
    '''Does not work with RHEL 8.
    '''
    pass


@pytest.mark.parametrize("lock_on_removal", [(True), (False)])
def test_lockscreen_password(local_user, lock_on_removal):
    """Local user unlocks screen using password, even if the smart card is
        inserted (after the password login). Screen unlocking requires the same
        method (PIN vs password) as was used for login.

    Test steps
        A. Configure SSSD:
            authselect select sssd with-smartcard
            with-smartcard-lock-on-removal
        B. Start GDM and insert password to log in
        C. Insert the smart card
        D. Lock the screen manually
        E. Wake up and unlock the screen using password

    Expected result
        A. Configuration is updated
        B. GDM starts and user logs in successfully
        C. Nothing happens
        D. The screen is locked
        E. Screen is unlocked succesfully
    """
    with Authselect(required=False, lock_on_removal=lock_on_removal), \
            GUI() as gui, \
            local_user.card(insert=False) as card:
        gui.click_on(local_user.username)
        gui.kb_write(local_user.password)
        gui.kb_send('enter', wait_time=20)
        gui.assert_text('Activities')

        card.insert()
        sleep(10)
        # press shortcut to lock the screen
        # keyboard.send('windows+l') cannot be parsed properly
        # this is a workaround for keyboard library
        keyboard.press((125, 126),)
        keyboard.send('l')
        keyboard.release((125, 126),)
        sleep(10)

        gui.wake_by_mouse()
        gui.kb_send('enter', screenshot=False)
        # Confirm that the screen is locked
        # After the screen has been locked, there should be no Activities
        gui.assert_no_text('Activities')
        # In RHEL 8, password box is already selected
        # and does not contain any text
        gui.kb_write(local_user.password)
        gui.kb_send('enter', wait_time=10)
        # confirm that you are logged back in
        gui.assert_text('Activities')
