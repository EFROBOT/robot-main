from core.servomoteur import init_servo, set_angle_servo


class Pince:
    def __init__(self, robot):
        self.robot = robot
        init_servo()

    def _attendre_fin_mouvement(self, timeout=10):
        ok = self.robot.mouvement_pince_termine.wait(timeout=timeout)
        if not ok:
            self.robot.logs.log("ERR", "Timeout mouvement pince")
        return ok

    def recuperer_caisses(self, recup, attendre=True, timeout=10):
        self.robot.mouvement_pince_termine.clear()
        self.robot.send_raw(f"Recuperer caisse {recup}")
        if attendre:
            ok = self._attendre_fin_mouvement(timeout=timeout)
            if not ok:
                self.robot.logs.log("ERR", f"Timeout récupération caisses ({recup})")
            return ok
        return True

    def pince_navigation(self):
        self.robot.send_raw("Pince Navigation")

    def pince_homologation(self):
        self.robot.send_raw("Pince Homologation")

    def pince_recuperer_avancer_et_stocker(self, rotation_active, attendre=True, timeout=10):
        self.robot.mouvement_pince_termine.clear()
        self.robot.send_raw(f"Pince_RecupererAvancerEtStocker {int(rotation_active)}")
        if attendre:
            ok = self._attendre_fin_mouvement(timeout=timeout)
            if not ok:
                self.robot.logs.log(
                    "ERR",
                    f"Timeout Pince_RecupererAvancerEtStocker ({rotation_active})",
                )
            return ok
        return True

    def pince_recuperer_et_stocker(self, rotation_active, attendre=True, timeout=10):
        self.robot.mouvement_pince_termine.clear()
        self.robot.send_raw(f"Pince_RecupererEtStocker {int(rotation_active)}")
        if attendre:
            ok = self._attendre_fin_mouvement(timeout=timeout)
            if not ok:
                self.robot.logs.log(
                    "ERR",
                    f"Timeout Pince_RecupererEtStocker ({rotation_active})",
                )
            return ok
        return True

    def securiser_caisses(self):
        set_angle_servo(103)

    def lacher_caisses(self):
        set_angle_servo(0)