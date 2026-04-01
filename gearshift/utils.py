ALLOWED = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED
